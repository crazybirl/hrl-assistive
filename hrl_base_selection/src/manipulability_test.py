#!/usr/bin/env python
import sys, optparse

import rospy, rospkg
import openravepy as op
import numpy as np
import math as m
import copy
from hrl_base_selection.srv import BaseMove_multi
import roslib; roslib.load_manifest('hrl_haptic_mpc')
import time
import roslib
roslib.load_manifest('hrl_base_selection')
roslib.load_manifest('hrl_haptic_mpc')
import rospy, rospkg
import tf
roslib.load_manifest('hrl_base_selection')
import hrl_lib.transforms as tr
import tf
import rospy
from visualization_msgs.msg import Marker
import time
from hrl_msgs.msg import FloatArrayBare
from helper_functions import createBMatrix
from data_reader import DataReader
from score_generator import ScoreGenerator
from pr2_controllers_msgs.msg import SingleJointPositionActionGoal

from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist

import pickle
import sPickle as pkl
roslib.load_manifest('hrl_lib')
from hrl_lib.util import load_pickle

class Manipulability_Testing(object):

    def __init__(self, subj=1):
        self.tf_listener = tf.TransformListener()
        self.subj = subj
        self.model = 'chair'
        self.visualize = False
        data_start = 0
        data_finish = 'end '  # 2000  # 4000 #'end'
        pos_clust = 20  # 10
        ori_clust = 2  # 2
        rospack = rospkg.RosPack()
        self.pkg_path = rospack.get_path('hrl_base_selection')
        print 'Loading scores.'
        self.loaded_scores = self.load_task('shaving', 'chair', subj)
        if self.loaded_scores is None:
            print 'The scores do not exist. Must generate scores! This may take a long time...'
            self.generate_scores(data_start, data_finish, pos_clust, ori_clust)
            print 'Scores generated. I will now continue.'
            print 'Now loading the scores I just generated'
            self.loaded_scores = self.load_task('shaving', 'chair', subj)
        if self.loaded_scores is None:
            print 'The scores still do not exist. This is bad. Fixes needed in code.'
            return
        headx = 0
        heady = 0
        self.scores = self.loaded_scores[headx, heady]
        model = 'chair'  # options are: 'chair', 'bed', 'autobed'
        task = 'shaving'
        subject = ''.join(['sub', str(self.subj), '_shaver'])
        print 'Reading in raw data from the task.'
        read_data = DataReader(subject=subject, data_start=data_start, data_finish=data_finish, model=model, task=task,
                             pos_clust=pos_clust, ori_clust=ori_clust,tf_listener=self.tf_listener)
        raw_data = read_data.get_raw_data()
        print 'Raw data is ready!'
        goal_data = read_data.generate_output_goals(test_goals=raw_data)
        # print 'Setting up openrave'
        # self.setup_openrave()
        print 'I will now pick base locations to evaluate. They will share the same reachability score, but will have' \
              ' differing manipulability scores.'
        # print 'before sorting:'
        # for i in xrange(10):
        #     print self.scores[i]
        self.scores = np.array(sorted(self.scores, key=lambda t: (t[1][1], t[1][2]), reverse=True))
        # print 'after sorting:'
        # for i in xrange(10):
        #     print self.scores[i]
        best_base = self.scores[0]
        if best_base[1][1] == 0:
            print 'There are no base locations with reachable goals. Something went wrong in the scoring or the setup'
        print 'The best base location is: \n', best_base
        comparison_bases = []
        max_num_of_comparisons = 3
        max_reach_count = 0
        print 'best base manip score is:', best_base[1][2]
        for i in xrange(len(self.scores)):
            if self.scores[i, 1][1] == best_base[1][1] and self.scores[i, 1][1] > 0:
                max_reach_count += 1
                # print self.scores[i,1][2]
        print 'The number of base configurations that can reach all clustered goals is: ',max_reach_count
        count = 0
        for i in np.arange(int(max_reach_count/max_num_of_comparisons), int(max_reach_count*3),
                           int(max_reach_count/max_num_of_comparisons)):
            print 'i: ',i
            if self.scores[int(i), 1][1] <= best_base[1][1] and self.scores[int(i), 1][1] > 0:
                comparison_bases.append(self.scores[i])

                # print self.scores[i,1][2]
                # if self.scores[i, 1][2] <= best_base[1][2]*(max_num_of_comparisons-count)/(max_num_of_comparisons+1):
                # if self.scores[i, 1][2] <= best_base[1][2]*m.pow(.9, count):
                    # comparison_bases.append(self.scores[i])
                    # count += 1
                    # if count > 5:
                    #     break
        # print 'number of base configurations that can reach all 20 clustered goal locations: ',count
        print 'The comparison base locations are:'
        for item in comparison_bases:
            print item
        print 'I may now proceed with comparison evaluation of the base locations with differing manipulability score'
        self.evaluate_base_locations(best_base, comparison_bases, goal_data)

    def evaluate_base_locations(self, best_base, comparison_bases, goal_data):
        visualize = False
        mytargets = 'all_goals'
        reference_options = []
        reference_options.append('head')
        myReferenceNames = reference_options
        myGoals = goal_data
        selector = ScoreGenerator(visualize=visualize, targets=mytargets, reference_names=myReferenceNames,
                                  goals=myGoals, model=self.model,tf_listener=self.tf_listener)
        selector.receive_new_goals(goal_data)
        best_base_score = selector.eval_init_config(best_base)
        # selector.show_rviz()
        print 'The score for the best base was: ', best_base_score
        comparison_base_scores = []
        for item in comparison_bases:
            selector.receive_new_goals(goal_data)
            comparison_base_scores.append(selector.eval_init_config(item))
        print 'The best base location is: \n', best_base
        print 'The score for the best base was: ', best_base_score
        for i in xrange(len(comparison_base_scores)):
            print 'A comparison base score for base: \n', comparison_bases[i]
            print 'The score was: ', comparison_base_scores[i]
        return best_base_score, comparison_base_scores

    def generate_scores(self, data_start, data_finish, pos_clust, ori_clust):
        model = 'chair'  # options are: 'chair', 'bed', 'autobed'
        task = 'shaving'
        subject = ''.join(['sub', str(self.subj), '_shaver'])

        start_time = time.time()
        print 'Starting to convert data!'
        runData = DataReader(subject=subject, data_start=data_start, data_finish=data_finish, model=model, task=task,
                             pos_clust=pos_clust, ori_clust=ori_clust, tf_listener=self.tf_listener)
        raw_data = runData.get_raw_data()

        ## To test clustering by using raw data sampled instead of clusters
        # sampled_raw = runData.sample_raw_data(raw_data, 100)
        # runData.generate_output_goals(test_goals=sampled_raw)

        # To run using the clustering system
        runData.cluster_data()
        runData.generate_output_goals()

        print 'Time to convert data into useful matrices: %fs'%(time.time()-start_time)
        print 'Now starting to generate the score. This will take a long time if there were many goal locations.'
        start_time = time.time()
        # runData.pub_rviz()
        # rospy.spin()
        # runData.plot_goals()
        runData.generate_score(viz_rviz=True, visualize=False, plot=False)
        print 'Time to generate all scores: %fs' % (time.time()-start_time)
        print 'Done generating the score sheet for this task and subject'

    def setup_openrave(self):
        # Setup Openrave ENV
        self.env = op.Environment()

        # Lets you visualize openrave. Uncomment to see visualization. Does not work through ssh.
        if self.visualize:
            self.env.SetViewer('qtcoin')

        ## Set up robot state node to do Jacobians. This works, but is commented out because we can do it with openrave
        #  fine.
        #torso_frame = '/torso_lift_link'
        #inertial_frame = '/base_link'
        #end_effector_frame = '/l_gripper_tool_frame'
        #from pykdl_utils.kdl_kinematics import create_kdl_kin
        #self.kinematics = create_kdl_kin(torso_frame, end_effector_frame)

        ## Load OpenRave PR2 Model
        self.env.Load('robots/pr2-beta-static.zae')
        self.robot = self.env.GetRobots()[0]
        v = self.robot.GetActiveDOFValues()
        v[self.robot.GetJoint('l_shoulder_pan_joint').GetDOFIndex()] = 3.14/2
        v[self.robot.GetJoint('r_shoulder_pan_joint').GetDOFIndex()] = -3.14/2
        v[self.robot.GetJoint('l_gripper_l_finger_joint').GetDOFIndex()] = .54
        v[self.robot.GetJoint('torso_lift_joint').GetDOFIndex()] = .3
        self.robot.SetActiveDOFValues(v)
        robot_start = np.matrix([[m.cos(0.), -m.sin(0.), 0., 0.],
                                 [m.sin(0.),  m.cos(0.), 0., 0.],
                                 [0.       ,         0., 1., 0.],
                                 [0.       ,         0., 0., 1.]])
        self.robot.SetTransform(np.array(robot_start))

        ## Set robot manipulators, ik, planner
        # IT IS PROBLEMATIC THAT I ONLY EVALUATE AT ONE SHOULDER POSITION. THIS NEEDS TO BE LOOKED AT AND REMEDIATED!!!
        # I think fixable by changing to 'leftarm_torso', but I am not certain.
        self.robot.SetActiveManipulator('leftarm')
        self.manip = self.robot.GetActiveManipulator()
        ikmodel = op.databases.inversekinematics.InverseKinematicsModel(self.robot, iktype=op.IkParameterization.Type.Transform6D)
        if not ikmodel.load():
            ikmodel.autogenerate()
        # create the interface for basic manipulation programs
        self.manipprob = op.interfaces.BaseManipulation(self.robot)

        ## Find and load Wheelchair Model
        rospack = rospkg.RosPack()
        pkg_path = rospack.get_path('hrl_base_selection')

        # Transform from the coordinate frame of the wc model in the back right bottom corner, to the head location on the floor
        if self.model == 'chair':
            '''
            self.env.Load(''.join([pkg_path, '/collada/wheelchair_rounded.dae']))
            originsubject_B_headfloor = np.matrix([[m.cos(0.), -m.sin(0.),  0.,      0.], #.45 #.438
                                                   [m.sin(0.),  m.cos(0.),  0.,      0.], #0.34 #.42
                                                   [       0.,         0.,  1.,      0.],
                                                   [       0.,         0.,  0.,      1.]])
            '''
            # This is the old wheelchair model
            self.env.Load(''.join([pkg_path, '/models/ADA_Wheelchair.dae']))
            self.originsubject_B_headfloor = np.matrix([[1., 0.,  0., .442603], #.45 #.438
                                                        [0., 1.,  0., .384275], #0.34 #.42
                                                        [0., 0.,  1.,      0.],
                                                        [0., 0.,  0.,      1.]])
            self.originsubject_B_originworld = copy.copy(self.originsubject_B_headfloor)

        elif self.model == 'bed':
            self.env.Load(''.join([pkg_path, '/models/head_bed.dae']))
            an = 0#m.pi/2
            self.originsubject_B_headfloor = np.matrix([[ m.cos(an),  0., m.sin(an),  .2954], #.45 #.438
                                                        [        0.,  1.,        0.,     0.], #0.34 #.42
                                                        [-m.sin(an),  0., m.cos(an),     0.],
                                                        [        0.,  0.,        0.,     1.]])
            self.originsubject_B_originworld = copy.copy(self.originsubject_B_headfloor)
        elif self.model == 'autobed':
            self.env.Load(''.join([pkg_path, '/collada/bed_and_body_v3_rounded.dae']))
            self.autobed = self.env.GetRobots()[1]
            v = self.autobed.GetActiveDOFValues()

            #0 degrees, 0 height
            v[self.autobed.GetJoint('head_rest_hinge').GetDOFIndex()] = 0.0
            v[self.autobed.GetJoint('tele_legs_joint').GetDOFIndex()] = -0.
            v[self.autobed.GetJoint('neck_body_joint').GetDOFIndex()] = -.1
            v[self.autobed.GetJoint('upper_mid_body_joint').GetDOFIndex()] = .4
            v[self.autobed.GetJoint('mid_lower_body_joint').GetDOFIndex()] = -.72
            v[self.autobed.GetJoint('body_quad_left_joint').GetDOFIndex()] = -0.4
            v[self.autobed.GetJoint('body_quad_right_joint').GetDOFIndex()] = -0.4
            v[self.autobed.GetJoint('quad_calf_left_joint').GetDOFIndex()] = 0.1
            v[self.autobed.GetJoint('quad_calf_right_joint').GetDOFIndex()] = 0.1
            v[self.autobed.GetJoint('calf_foot_left_joint').GetDOFIndex()] = .02
            v[self.autobed.GetJoint('calf_foot_right_joint').GetDOFIndex()] = .02
            v[self.autobed.GetJoint('body_arm_left_joint').GetDOFIndex()] = -.12
            v[self.autobed.GetJoint('body_arm_right_joint').GetDOFIndex()] = -.12
            v[self.autobed.GetJoint('arm_forearm_left_joint').GetDOFIndex()] = 0.05
            v[self.autobed.GetJoint('arm_forearm_right_joint').GetDOFIndex()] = 0.05
            v[self.autobed.GetJoint('forearm_hand_left_joint').GetDOFIndex()] = -0.1
            v[self.autobed.GetJoint('forearm_hand_right_joint').GetDOFIndex()] = -0.1
            #v[self.autobed.GetJoint('leg_rest_upper_joint').GetDOFIndex()]= -0.1
            self.autobed.SetActiveDOFValues(v)
            self.env.UpdatePublishedBodies()
            headmodel = self.autobed.GetLink('head_link')
            head_T = np.matrix(headmodel.GetTransform())
            an = 0#m.pi/2
            self.originsubject_B_headfloor = np.matrix([[1.,  0., 0.,  head_T[0, 3]],  #.45 #.438
                                                        [0.,  1., 0.,  head_T[1, 3]],  # 0.34 #.42
                                                        [0.,  0., 1.,           0.],
                                                        [0.,  0., 0.,           1.]])
            self.originsubject_B_originworld = np.matrix(np.eye(4))
        else:
            print 'I got a bad model. What is going on???'
            return None
        self.subject = self.env.GetBodies()[1]
        # self.subject_location = originsubject_B_headfloor.I
        self.subject.SetTransform(np.array(self.originsubject_B_originworld.I))

        print 'OpenRave has succesfully been initialized. \n'



    def initialize_test_conditions(self):
        angle = -m.pi/2
        pr2_B_head1 = np.matrix([[   m.cos(angle),  -m.sin(angle),          0.,        0.],
                                 [   m.sin(angle),   m.cos(angle),          0.,       2.5],
                                 [             0.,             0.,          1.,    1.1546],
                                 [             0.,             0.,          0.,        1.]])
        an = -m.pi/2
        pr2_B_head2 = np.matrix([[  m.cos(an),   0.,  m.sin(an),       0.],
                                 [         0.,   1.,         0.,       0.],
                                 [ -m.sin(an),   0.,  m.cos(an),       0.],
                                 [         0.,   0.,         0.,       1.]])
        pr2_B_head=pr2_B_head1*pr2_B_head2
        pos_goal = [pr2_B_head[0, 3], pr2_B_head[1, 3], pr2_B_head[2, 3]]
        ori_goal = tr.matrix_to_quaternion(pr2_B_head[0:3, 0:3])
        psm_head = PoseStamped()
        psm_head.header.frame_id = '/base_link'
        psm_head.pose.position.x = pos_goal[0]
        psm_head.pose.position.y = pos_goal[1]
        psm_head.pose.position.z = pos_goal[2]
        psm_head.pose.orientation.x = ori_goal[0]
        psm_head.pose.orientation.y = ori_goal[1]
        psm_head.pose.orientation.z = ori_goal[2]
        psm_head.pose.orientation.w = ori_goal[3]
        head_pub = rospy.Publisher("/haptic_mpc/head_pose", PoseStamped, latch=True)
        head_pub.publish(psm_head)

    def score_goal_locations(self):
        task = 'shaving_test'
        # task = 'yogurt'
        model = 'chair'

        start_time = time.time()
        rospy.wait_for_service('select_base_position')
        try:
            #select_base_position = rospy.ServiceProxy('select_base_position', BaseMove)
            #response = select_base_position(psm_goal, psm_head)
            select_base_position = rospy.ServiceProxy('select_base_position', BaseMove_multi)
            response = select_base_position(task, model)
            print 'response is: \n', response
            print 'Total time for service to return the response was: %fs' % (time.time()-start_time)
            return response.base_goal, response.configuration_goal#, response.ik_solution
        except rospy.ServiceException, e:
            print "Service call failed: %s"%e

    def load_task(self, task, model, subj):
        file_name = ''.join([self.pkg_path, '/data/', task, '_', model, '_subj_', str(subj), '_score_data.pkl'])
        return self.load_spickle(file_name)

    ## read a pickle and return the object.
    # @param filename - name of the pkl
    # @return - object that had been pickled.
    def load_spickle(self, filename):
        try:
            p = open(filename, 'rb')
        except IOError:
            print "hrl_lib.util: Pickle file cannot be opened."
            return None
        try:
            picklelicious = pkl.load(p)
        except ValueError:
            print 'load_spickle failed once, trying again'
            p.close()
            p = open(filename, 'rb')
            picklelicious = pkl.load(p)
        p.close()
        return picklelicious


if __name__ == "__main__":
    rospy.init_node('manip_test')
    myTest = Manipulability_Testing(subj=6)
    rospy.spin()
    # myTest.initialize_test_conditions()
    # myTest.evaluate_task()











