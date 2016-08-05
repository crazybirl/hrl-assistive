#!/usr/bin/env python

from collections import deque

import rospy, rosparam, rospkg, roslib
import actionlib
from threading import RLock
import math as m
import rospy, rosparam, rospkg, roslib
from hrl_msgs.msg import FloatArrayBare
from std_msgs.msg import String, Int32, Int8, Bool
from actionlib_msgs.msg import GoalStatus
# from actionlib_msgs.msg import GoalStatus as GS
from geometry_msgs.msg import PoseStamped
import tf
from hrl_task_planning.msg import PDDLState
from hrl_pr2_ar_servo.msg import ARServoGoalData
from hrl_base_selection.srv import BaseMove_multi
from hrl_srvs.srv import None_Bool, None_BoolResponse
from pr2_controllers_msgs.msg import SingleJointPositionActionGoal, SingleJointPositionAction, SingleJointPositionGoal
# pylint: disable=W0102
from task_smacher import PDDLSmachState


SPA = ["succeeded", "preempted", "aborted"]


def get_action_state(domain, problem, action, args, init_state, goal_state):
    if action == 'FIND_TAG':
        return FindTagState(domain=domain, model=args[0], problem=problem,
                            action=action, action_args=args,
                            init_state=init_state, goal_state=goal_state,
                            outcomes=SPA)
    if action == 'TRACK_TAG':
        return TrackTagState(domain=domain, model=args[0], problem=problem,
                             action=action, action_args=args,
                             init_state=init_state, goal_state=goal_state,
                             outcomes=SPA)
    elif action == 'CONFIGURE_MODEL_ROBOT':
        return ConfigureModelRobotState(domain=domain, task=args[0], model=args[1], problem=problem,
                                        action=action, action_args=args,
                                        init_state=init_state, goal_state=goal_state,
                                        outcomes=SPA)
    elif action == 'CHECK_OCCUPANCY':
        return CheckOccupancyState(domain=domain, model=args[0], problem=problem,
                                   action=action, action_args=args, init_state=init_state,
                                   goal_state=goal_state, outcomes=SPA)
    elif action == 'REGISTER_HEAD':
        return RegisterHeadState(domain=domain, model=args[0], problem=problem,
                                 action=action, action_args=args, init_state=init_state,
                                 goal_state=goal_state, outcomes=SPA)
    elif action == 'CALL_BASE_SELECTION':
        return CallBaseSelectionState(task=args[0], model=args[1], domain=domain, problem=problem,
                                      action=action, action_args=args, init_state=init_state,
                                      goal_state=goal_state, outcomes=SPA)
    elif action == 'MOVE_ROBOT':
        return MoveRobotState(domain=domain, task=args[0], model=args[1], problem=problem, action=action, action_args=args, init_state=init_state, goal_state=goal_state, outcomes=SPA)
    elif action == 'MOVE_ARM':
        return MoveArmState(task=args[0], model=args[1], domain=domain, problem=problem, action=action, action_args=args, init_state=init_state, goal_state=goal_state, outcomes=SPA)
    elif action == 'DO_TASK':
        return PDDLSmachState(domain=domain, problem=problem, action=action, action_args=args, init_state=init_state, goal_state=goal_state, outcomes=SPA)



class FindTagState(PDDLSmachState):
    def __init__(self, model, domain, *args, **kwargs):
        super(FindTagState, self).__init__(domain=domain, *args, **kwargs)
        self.start_finding_AR_publisher = rospy.Publisher('find_AR_now', Bool, queue_size=1)
        self.domain = domain
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)
        self.model = model
        self.ar_tag_found = False

    def on_execute(self, ud):
        print "Start Looking For Tag"
        self.start_finding_AR_publisher.publish(True)
        print "Waiting to see if tag found"
        rospy.Subscriber('AR_acquired', Bool, self.found_ar_tag_cb)
        while not rospy.is_shutdown():
            if self.ar_tag_found:
                print "Tag FOUND"
                rospy.loginfo("AR Tag Found")
                state_update = PDDLState()
                state_update.domain = self.domain
                state_update.predicates = ['(FOUND-TAG %s)' % self.model]
                print "Publishing (FOUND-TAG) update"
                self.state_pub.publish(state_update)
                return
            rospy.sleep(1)

    def found_ar_tag_cb(self, msg):
        found_ar_tag = msg.data
        if found_ar_tag:
            self.ar_tag_found = True


class TrackTagState(PDDLSmachState):
    def __init__(self, model, domain, *args, **kwargs):
        super(TrackTagState, self).__init__(domain=domain, *args, **kwargs)
        self.start_tracking_AR_publisher = rospy.Publisher('track_AR_now', Bool, queue_size=1)
        self.model = model

    def on_execute(self, ud):
        print "Starting to track AR Tag"
        self.start_tracking_AR_publisher.publish(True)


class RegisterHeadState(PDDLSmachState):
    def __init__(self, model, domain, *args, **kwargs):
        super(RegisterHeadState, self).__init__(domain=domain, *args, **kwargs)
        self.listener = tf.TransformListener()
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)
        self.model = model
        print "Looking for head of person on: %s" % model

    def on_execute(self, ud):
        head_registered = self.get_head_pose()
        if head_registered:
            print "Head Found."
            state_update = PDDLState()
            state_update.domain = self.domain
            state_update.predicates = ['(HEAD-REGISTERED %s)' % self.model]
            print "Publishing (HEAD-REGISTERED) update"
            self.state_pub.publish(state_update)
        else:
            print "Head NOT Found"
            return 'aborted'

    def get_head_pose(self, head_frame="/user_head_link"):
        try:
            now = rospy.Time.now()
            print "[%s] Register Head State Waiting for Head Transform" % rospy.get_name()
            self.listener.waitForTransform("/base_link", head_frame, now, rospy.Duration(5))
            pos, quat = self.listener.lookupTransform("/base_link", head_frame, now)
            return True
        except Exception as e:
            rospy.loginfo("TF Exception:\r\n%s" %e)
            return False


class CheckOccupancyState(PDDLSmachState):
    def __init__(self, model, domain, *args, **kwargs):
        super(CheckOccupancyState, self).__init__(domain=domain, *args, **kwargs)
        self.model = model
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)
#        print "Check Occupancy of Model: %s" % model
        if model.upper() == 'AUTOBED':
            self.autobed_occupied_status = False

    def on_execute(self, ud):
        if self.model.upper() == 'AUTOBED':
            print "[%s] Check Occupancy State Waiting for Service" % rospy.get_name()
            rospy.wait_for_service('autobed_occ_status')
            try:
                self.AutobedOcc = rospy.ServiceProxy('autobed_occ_status', None_Bool)
                self.autobed_occupied_status = self.AutobedOcc().data
            except rospy.ServiceException, e:
                print "Service call failed: %s" % e
                return 'aborted'

            if self.autobed_occupied_status:
                state_update = PDDLState()
                state_update.domain = self.domain
                state_update.predicates = ['(OCCUPIED %s)' % self.model]
                self.state_pub.publish(state_update)
                self.goal_reached = False
            else:
                self.goal_reached = False
                return 'aborted'


class MoveArmState(PDDLSmachState):
    def __init__(self, task, model, domain, *args, **kwargs):
        super(MoveArmState, self).__init__(domain=domain, *args, **kwargs)
        self.l_arm_pose_pub = rospy.Publisher('/left_arm/haptic_mpc/goal_pose', PoseStamped, queue_size=1)
        self.domain = domain
        self.task = task
        self.model = model
        self.goal_reached = False
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)

    def arm_reach_goal_cb(self, msg):
        self.goal_reached = msg.data

    def publish_goal(self):
        goal = PoseStamped()
        if self.task == 'scratching_knee_left':
            goal.pose.position.x = -0.06310556
            goal.pose.position.y = 0.07347758+0.05
            goal.pose.position.z = 0.00485197
            goal.pose.orientation.x = 0.48790861
            goal.pose.orientation.y = -0.50380292
            goal.pose.orientation.z = 0.51703901
            goal.pose.orientation.w = -0.4907122
            goal.header.frame_id = '/autobed/calf_left_link'
            rospy.loginfo('[%s] Reaching to left knee.' % rospy.get_name())

        elif self.task == 'wiping_mouth':
            goal.pose.position.x = 0.17
            goal.pose.position.y = 0.
            goal.pose.position.z = -0.16
            goal.pose.orientation.x = 0.
            goal.pose.orientation.y = 0.
            goal.pose.orientation.z = 1.
            goal.pose.orientation.w = 0.
            goal.header.frame_id = '/autobed/head_link'
            rospy.loginfo('[%s] Reaching to mouth.' % rospy.get_name())
        else:
            rospy.logwarn('[%s] Cannot Find ARM GOAL to reach. Have you specified the right task?' % rospy.get_name())
            return False
        self.l_arm_pose_pub.publish(goal)
        return True
    def on_execute(self, ud):
        publish_stat = self.publish_goal()
        if not publish_stat:
            return 'aborted' 
        #Now that goal is published, we wait until goal is reached
        rospy.Subscriber("haptic_mpc/in_deadzone", std_msgs.msg.Bool, self.arm_reach_goal_cb)
        while not rospy.is_shutdown() and not self.goal_reached:
            rospy.sleep(1)
            
        if self.goal_reached:
            rospy.loginfo("[%s] Arm Goal Reached" % rospy.get_name())
            state_update = PDDLState()
            state_update.domain = self.domain
            state_update.predicates = ['ARM-REACHED' + ' ' + str(self.task) + ' ' + str(self.model)]
            print "Publishing (ARM-REACHED) update"
            self.state_pub.publish(state_update)


class MoveRobotState(PDDLSmachState):
    def __init__(self, task, model, domain, *args, **kwargs):
        super(MoveRobotState, self).__init__(domain=domain, *args, **kwargs)
        self.model = model
        self.task = task
        self.domain = domain
        self.goal_reached = False
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)
        rospy.loginfo('[%s] Ready to move! Click to move PR2 base!' % rospy.get_name())
        rospy.loginfo('[%s] Remember: The AR tag must be tracked before moving!' % rospy.get_name())

    def base_servoing_cb(self, msg):
        if msg.data == 5:
            self.goal_reached = True


    def on_execute(self, ud):
        rospy.loginfo('[%s] Moving PR2 Base' % rospy.get_name())
        try:
            base_goals = rospy.get_param('/pddl_tasks/%s/base_goals' % self.domain)
        except:
            rospy.logwarn("[%s] MoveRobotState - Cannot find base location on parameter server", rospy.get_name())
            return 'aborted'
        pr2_goal_pose = PoseStamped()
        pr2_goal_pose.header.stamp = rospy.Time.now()
        pr2_goal_pose.header.frame_id = 'base_footprint'
        trans_out = base_goals[:3]
        rot_out = base_goals[3:]
        pr2_goal_pose.pose.position.x = trans_out[0]
        pr2_goal_pose.pose.position.y = trans_out[1]
        pr2_goal_pose.pose.position.z = trans_out[2]
        pr2_goal_pose.pose.orientation.x = rot_out[0]
        pr2_goal_pose.pose.orientation.y = rot_out[1]
        pr2_goal_pose.pose.orientation.z = rot_out[2]
        pr2_goal_pose.pose.orientation.w = rot_out[3]
        goal = ARServoGoalData()
        goal.tag_id = 4
        goal.marker_topic = '/ar_pose_marker'
        goal.tag_goal_pose = pr2_goal_pose
        self.servo_goal_pub.publish(goal)
        rospy.Subscriber('/pr2_ar_servo/state_feedback', Int8, self.base_servoing_cb)
        while not rospy.is_shutdown() and not self.goal_reached:
            rospy.sleep(1)
        if self.goal_reached:
            rospy.loginfo("[%s] Base Goal Reached" % rospy.get_name())
            state_update = PDDLState()
            state_update.domain = self.domain
            state_update.predicates = ['(BASE-REACHED %s %s)' % (self.task, self.model)]
            self.state_pub.publish(state_update)


class CallBaseSelectionState(PDDLSmachState):
    def __init__(self, task, model, domain, *args, **kwargs):
        super(CallBaseSelectionState, self).__init__(domain=domain, *args, **kwargs)
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)
        print "Base Selection Called for task: %s and Model: %s" %(task, model)
        self.domain = domain
        self.task = task
        self.model = model

    def call_base_selection(self):
        rospy.loginfo("[%s] Calling base selection. Please wait." %rospy.get_name())
        rospy.wait_for_service("select_base_position")
        self.base_selection_client = rospy.ServiceProxy("select_base_position", BaseMove_multi)

        if self.task.upper() == 'WIPING_MOUTH':
            local_task_name = 'wiping_face'

        try:
            self.model = 'autobed'
            resp = self.base_selection_client(local_task_name, self.model)
        except rospy.ServiceException as se:
            rospy.logerr(se)
            return [None, None]
        return resp.base_goal, resp.configuration_goal

    def on_execute(self, ud):
        base_goals = []
        configuration_goals = []
        goal_array, config_array = self.call_base_selection()
        if goal_array == None or config_array == None:
            print "Base Selection Returned None"
            return 'aborted'
        for item in goal_array[:7]:
            base_goals.append(item)
        for item in config_array[:3]:
            configuration_goals.append(item)
        print "Base Goals returned:\r\n", base_goals
        print "Configuration Goals returned:\r\n", configuration_goals
        try:
            rospy.set_param('/pddl_tasks/%s/base_goals' % self.domain, base_goals)
        except:
            rospy.logwarn("[%s] CallBaseSelectionState - Cannot place base goal on parameter server", rospy.get_name())
            return 'aborted'
        try:
            rospy.set_param('/pddl_tasks/%s/configuration_goals' % self.domain, configuration_goals)
        except:
            rospy.logwarn("[%s] CallBaseSelectionState - Cannot place autoebed and torso height config on parameter server", rospy.get_name())
            return 'aborted'
        state_update = PDDLState()
        state_update.domain = self.domain
        state_update.predicates = ['(BASE-SELECTED %s %s)' % (self.task, self.model)]
        print "Publishing (BASE-SELECTED) update"
        self.state_pub.publish(state_update)


class ConfigureModelRobotState(PDDLSmachState):
    def __init__(self, task, model, domain, *args, **kwargs):
        super(ConfigureModelRobotState, self).__init__(domain=domain, *args, **kwargs)
        self.domain = domain
        self.task = task
        self.model = model
        print "Configuring Model and Robot for task: %s and Model: %s" %(task, model)
        if self.model.upper() == 'AUTOBED':
            self.model_reached = False
        else:
            self.model_reached = True
        self.torso_reached = False
        self.state_pub = rospy.Publisher('/pddl_tasks/state_updates', PDDLState, queue_size=10, latch=True)
        self.torso_client = actionlib.SimpleActionClient('torso_controller/position_joint_action',
                                                         SingleJointPositionAction)
        if self.model.upper() == 'AUTOBED':
            self.bed_state_leg_theta = None
            self.autobed_pub = rospy.Publisher('/abdin0', FloatArrayBare, queue_size=1, latch=True)

    def bed_state_cb(self, data):
        self.bed_state_leg_theta = data.data[2]

    def bed_status_cb(self, data):
        self.model_reached = data.data

    def on_execute(self, ud):
        rospy.loginfo("[%s] Waiting for torso_controller/position_joint_action server" % rospy.get_name())
        if self.torso_client.wait_for_server(rospy.Duration(5)):
            rospy.loginfo("[%s] Found torso_controller/position_joint_action server" % rospy.get_name())
        else:
            rospy.logwarn("[%s] Cannot find torso_controller/position_joint_action server" % rospy.get_name())
            return 'aborted'

        if self.model.upper() == 'AUTOBED':
            self.autobed_sub = rospy.Subscriber('/abdout0', FloatArrayBare, self.bed_state_cb)
            try:
                self.configuration_goal = rospy.get_param('/pddl_tasks/%s/configuration_goals' % self.domain)
            except:
                rospy.logwarn("[%s] ConfigurationGoalState - Cannot find spine height and autobed config on parameter server" % rospy.get_name())
                return 'aborted'
            while (self.bed_state_leg_theta is None):
                rospy.sleep(1)
            autobed_goal = FloatArrayBare()
            autobed_goal.data = ([self.configuration_goal[2],
                                  self.configuration_goal[1],
                                  self.bed_state_leg_theta])
            self.autobed_pub.publish(autobed_goal)
            rospy.Subscriber('abdstatus0', Bool, self.bed_status_cb)

            if self.configuration_goal[0] is not None:
                torso_lift_msg = SingleJointPositionGoal()
                torso_lift_msg.position = self.configuration_goal[0]
                print "TORSO!!! Move TO:"
                print self.configuration_goal[0]
                self.torso_client.send_goal(torso_lift_msg)
            else:
                rospy.logwarn("[%s] Some problem in getting TORSO HEIGHT from base selection" % rospy.get_name())
                return 'aborted'
            rospy.loginfo("[%s] Waiting For Torso to be moved" % rospy.get_name())
            self.torso_client.wait_for_result()
            torso_status = self.torso_client.get_state()
            if torso_status == GoalStatus.SUCCEEDED:
                rospy.loginfo("[%s] TORSO Actionlib Client has SUCCEEDED" % rospy.get_name())
                state_update = PDDLState()
                state_update.domain = self.domain
                state_update.predicates = ['(CONFIGURED SPINE %s %s)' % (self.task, self.model)]
                print "Publishing (CONFIGURED SPINE) update"
                self.state_pub.publish(state_update)
            else:
                rospy.logwarn("[%s] Torso Actionlib Client has NOT succeeded" % rospy.get_name())
                return 'aborted'

            while not rospy.is_shutdown() and not self.model_reached:
                rospy.sleep(1)
            
            rospy.loginfo("[%s] Waiting For Model to be moved" % rospy.get_name())
            if self.model_reached:
                rospy.loginfo("[%s] Bed Goal Reached" % rospy.get_name())
                state_update = PDDLState()
                state_update.domain = self.domain
                state_update.predicates = ['(CONFIGURED BED %s %s)' % (self.task, self.model)]
                print "Publishing (CONFIGURED BED) update"
                self.state_pub.publish(state_update)

