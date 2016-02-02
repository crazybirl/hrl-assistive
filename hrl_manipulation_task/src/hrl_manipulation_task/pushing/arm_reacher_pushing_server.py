#!/usr/bin/env python
#
# Copyright (c) 2014, Georgia Tech Research Corporation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Georgia Tech Research Corporation nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY GEORGIA TECH RESEARCH CORPORATION ''AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL GEORGIA TECH BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

#  \author Daehyung Park (Healthcare Robotics Lab, Georgia Tech.)

# System
import sys, time, copy
import numpy as np

# ROS
import rospy, roslib
import tf
import PyKDL
from geometry_msgs.msg import Pose, PoseStamped, Point, Quaternion
from std_msgs.msg import String

# HRL library
import hrl_haptic_mpc.haptic_mpc_util as haptic_mpc_util
import hrl_lib.quaternion as quatMath 
from hrl_srvs.srv import None_Bool, String_String

# Personal library
from sandbox_dpark_darpa_m3.lib.hrl_mpc_base import mpcBaseAction


class armReachAction(mpcBaseAction):
    def __init__(self, d_robot, controller, arm, tool_id=0, verbose=False):
        mpcBaseAction.__init__(self, d_robot, controller, arm, tool_id)

        #Variables...! #
        self.stop_motion = False
        self.verbose = verbose

        self.default_frame      = PyKDL.Frame()

        self.initCommsForArmReach()                            
        self.initParamsForArmReach()

        rate = rospy.Rate(100) # 25Hz, nominally.
        while not rospy.is_shutdown():
            if self.getJointAngles() != []:
                if verbose:
                    print "--------------------------------"
                    print "Current "+self.arm_name+" arm joint angles"
                    print self.getJointAngles()
                    print "Current "+self.arm_name+" arm pose"
                    print self.getEndeffectorPose(tool=tool_id)
                    print "Current "+self.arm_name+" arm orientation (w/ euler rpy)"
                    print self.getEndeffectorRPY(tool=tool_id) #*180.0/np.pi
                    print "--------------------------------"
                break
            rate.sleep()
            
        rospy.loginfo("Arm Reach Action is initialized.")
                            
    def initCommsForArmReach(self):

        # publishers and subscribers
        rospy.Subscriber('InterruptAction', String, self.stopCallback)
        
        # service
        self.reach_service = rospy.Service('arm_reach_enable', String_String, self.serverCallback)
        ## rospy.Subscriber('/ar_track_alvar/artag_vision_pose_0', PoseStamped, self.tagPoseCallback)

        if self.verbose: rospy.loginfo("ROS-based communications are set up .")
                                    
    def initParamsForArmReach(self):
        '''
        Industrial movment commands generally follows following format, 
        
               Movement type, joint or pose(pos+euler), timeout, relative_frame(not implemented)

        In this code, we allow to use following movement types,

        MOVEP: straight motion without orientation control (ex. MOVEP pos-euler timeout relative_frame)
        MOVES: straight motion with orientation control (ex. MOVES pos-euler timeout relative_frame)
        MOVET: MOVES with respect to the current tool frame (ex. MOVET pos-euler timeout) (experimental!!)
        MOVEJ: joint motion (ex. MOVEJ joint timeout)
        PAUSE: Add pause time between motions (ex. PAUSE duration)

        #TOOL: Set a tool frame for MOVET. Defualt is 0 which is end-effector frame.

        joint or pose: we use radian and meter unit. The order of euler angle follows original z-y-x order (RPY).
        timeout or duration: we use second
        relative_frame: You can put your custome PyKDL frame variable or you can use 'self.default_frame'
        '''
        
        self.motions = {}

        ## Pushing white microwave motoins --------------------------------------------------------
        # It uses the l_gripper_push_frame
        self.motions['initMicroWhite'] = {}
        self.motions['initMicroWhite']['left'] = \
          [['MOVEJ', '[-1.19, 0.667, -0.36, -1.63, 4.32, -1.02, -2.007]', 5.0]] 
        self.motions['initMicroWhite']['right'] = []

        self.motions['runMicroWhite'] = {}
        self.motions['runMicroWhite']['left'] = \
          [['MOVEJ', '[-1.19, 0.667, -0.36, -1.63, 4.32, -1.02, -2.007]', 5.0]] 
        self.motions['runMicroWhite']['right'] = []


        ## Pushing cabinet motoins --------------------------------------------------------
        # It uses the l_gripper_spoon_frame aligned with mouth
        self.motions['initCabinet'] = {}
        self.motions['initCabinet']['left'] = \
          [] 
        self.motions['initCabinet']['right'] = \
        [['MOVEJ', '[-1.19, 0.667, -0.36, -1.63, 4.32, -1.02, -2.007]', 5.0]]

        self.motions['runCabinet'] = {}
        self.motions['runCabinet']['left'] = \
          []
        self.motions['runCabinet']['right'] = \
          [['MOVET', '[0., 0., -0.2, 0., 0., 0.]', 10., 'self.default_frame'],
           ['MOVET', '[0.2, 0., 0, 0., 0., 0.]', 10., 'self.default_frame'],
           ['MOVET', '[-0.2, 0., 0, 0., 0., 0.]', 10., 'self.default_frame'],
           ['MOVET', '[0., 0., 0.2, 0., 0., 0.]', 10., 'self.default_frame'],
           ]
                                                    
        rospy.loginfo("Parameters are loaded.")
                
        
    def serverCallback(self, req):
        req = req.data
        self.stop_motion = False

        self.parsingMovements(self.motions[req][self.arm_name])
        return "Completed to execute "+req 

    
    def stopCallback(self, msg):
        print '\n\nAction Interrupted! Event Stop\n\n'
        print 'Interrupt Data:', msg.data
        self.stop_motion = True

        print "Stopping Motion..."
        self.setStop() #Stops Current Motion
        try:
            self.setStopRight() #Sends message to service node
        except:
            rospy.loginfo("Couldn't stop "+self.arm_name+" arm! ")





if __name__ == '__main__':

    import optparse
    p = optparse.OptionParser()
    haptic_mpc_util.initialiseOptParser(p)
    opt = haptic_mpc_util.getValidInput(p)

    # Initial variables
    d_robot    = 'pr2'
    controller = 'static'
    #controller = 'actionlib'
    arm        = opt.arm
    tool_id    = 2
    if opt.arm == 'l': verbose = False
    else: verbose = True
        
    rospy.init_node('arm_reacher_pushing')
    ara = armReachAction(d_robot, controller, arm, tool_id, verbose)
    rospy.spin()


