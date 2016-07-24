import os, sys
import numpy as np


def getScooping(task, data_renew, AE_renew, HMM_renew, rf_center='kinEEPos', local_range=10.0, \
                pre_train=False,\
                ae_swtch=False, dim=4):

    if dim == 4:
        handFeatures = ['unimodal_ftForce',\
                        'crossmodal_targetEEDist', \
                        'crossmodal_targetEEAng', \
                        'unimodal_audioWristRMS']
        HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 3.566, 'scale': 1.0,
                          'add_logp_d': True}
        SVM_param_dict = {'renew': False, 'w_negative': 4.0, 'gamma': 0.039, 'cost': 4.59,\
                          'hmmosvm_nu': 0.00316,\
                          'hmmsvm_diag_w_negative': 0.85, 'hmmsvm_diag_cost': 12.5, \
                          'hmmsvm_diag_gamma': 0.01,\
                          'osvm_nu': 0.000215, 'raw_window_size': 10,\
                          'hmmsvm_dL_w_negative': 0.85, 'hmmsvm_dL_cost': 7.5, \
                          'hmmsvm_dL_gamma': 0.50749,
                          'hmmsvm_LSLS_cost': 15.0,\
                          'hmmsvm_LSLS_gamma': 0.01, \
                          'hmmsvm_LSLS_w_negative': 0.2,
                          }
        
        nPoints        = 20  # 'progress_time_cluster',,'fixed' , 'svm' , 
        ROC_param_dict = {'methods': [ 'svm' ],\
                          'update_list': ['svm'],\
                          'nPoints': nPoints,\
                          'progress_param_range':np.linspace(0.0, -7., nPoints), \
                          'svm_param_range': np.logspace(1.4, 1.45, nPoints),\
                          'change_param_range': np.logspace(-0.8, 1.0, nPoints)*-1.0,\
                          'fixed_param_range': np.logspace(0.0, 0.5, nPoints)*-1.0+1.3,\
                          'cssvm_param_range': np.logspace(-4.0, 2.0, nPoints),\
                          'hmmosvm_param_range': np.logspace(-4.0, 1.0, nPoints),\
                          'hmmsvm_diag_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmsvm_dL_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmsvm_LSLS_param_range': np.logspace(-4, 1.2, nPoints),\
                          'osvm_param_range': np.logspace(-5., 0.0, nPoints),\
                          'sgd_param_range': np.logspace(1.0, 1.5, nPoints)}

        AD_param_dict = {'svm_w_positive': 1.0, 'sgd_w_positive': 1.0, 'sgd_n_iter': 20}
        
    elif dim == 3:
        handFeatures = ['unimodal_ftForce',\
                        'crossmodal_targetEEDist', \
                        'crossmodal_targetEEAng']
        HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 3.566, 'scale': 3.0,\
                          'add_logp_d': True}
        SVM_param_dict = {'renew': False, 'w_negative': 0.825, 'gamma': 3.16, 'cost': 4.0,\
                          'hmmosvm_nu': 0.00316,\
                          'hmmsvm_diag_w_negative': 0.85, 'hmmsvm_diag_cost': 12.5, \
                          'hmmsvm_diag_gamma': 0.01}

        nPoints        = 20  # 'progress_time_cluster',,'fixed' , 'svm' , 
        ROC_param_dict = {'methods': [ 'fixed', 'progress_time_cluster', 'svm', 'hmmosvm'],\
                          'update_list': ['hmmosvm'],\
                          'nPoints': nPoints,\
                          'progress_param_range':np.linspace(-0.8, -5., nPoints), \
                          'svm_param_range': np.logspace(-2.5, 0, nPoints),\
                          'fixed_param_range': np.linspace(0.0, -1.5, nPoints),\
                          'cssvm_param_range': np.logspace(-4.0, 2.0, nPoints),\
                          ## 'svm_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmosvm_param_range': np.logspace(-4.0, 1.0, nPoints),\
                          'osvm_param_range': np.linspace(0.1, 2.0, nPoints),\
                          'sgd_param_range': np.logspace(-4, 1.2, nPoints)}        
        AD_param_dict = {'svm_w_positive': 0.1, 'sgd_w_positive': 1.0}
        
    elif dim == 2:
        handFeatures = ['unimodal_ftForce',\
                        'crossmodal_targetEEDist' ]
        HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 1.4, 'scale': 3.0,\
                          'add_logp_d': True}
        SVM_param_dict = {'renew': False, 'w_negative': 3.5, 'gamma': 0.0147, 'cost': 3.0,\
                          'hmmosvm_nu': 0.00316}

        nPoints        = 20  # 'progress_time_cluster',,'fixed' , 'svm' , 
        ROC_param_dict = {'methods': [ 'fixed', 'progress_time_cluster', 'svm', 'hmmosvm'],\
                          'update_list': ['hmmosvm'],\
                          'nPoints': nPoints,\
                          'progress_param_range':np.linspace(-0.8, -8., nPoints), \
                          'svm_param_range': np.logspace(-1.5, 1, nPoints),\
                          'fixed_param_range': np.linspace(0.2, -3.0, nPoints),\
                          'cssvm_param_range': np.logspace(-4.0, 2.0, nPoints),\
                          ## 'svm_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmosvm_param_range': np.logspace(-4.0, 1.5, nPoints),\
                          'osvm_param_range': np.linspace(0.1, 2.0, nPoints),\
                          'sgd_param_range': np.logspace(-4, 1.2, nPoints)}        
        AD_param_dict = {'svm_w_positive': 1.0, 'sgd_w_positive': 1.0}
        
    rawFeatures = ['relativePose_target_EE', \
                   'wristAudio', \
                   'ft' ]                                
    modality_list = ['kinematics', 'audioWrist', 'ft', 'vision_landmark', \
                     'vision_change', 'pps']
    raw_data_path  = '/home/dpark/hrl_file_server/dpark_data/anomaly/ICRA2017/'

    AE_param_dict  = {'renew': AE_renew, 'switch': ae_swtch, 'method': 'ae', 'time_window': 4,  \
                      'layer_sizes':[], 'learning_rate':1e-4, \
                      'learning_rate_decay':1e-6, \
                      'momentum':1e-6, 'dampening':1e-6, 'lambda_reg':1e-6, \
                      'max_iteration':100000, 'min_loss':0.01, 'cuda':True, \
                      'pca_gamma': 1.0,\
                      'filter':False, 'filterDim':4, \
                      'nAugment': 1, \
                      'add_option': None, 'rawFeatures': rawFeatures,\
                      'add_noise_option': [], 'preTrainModel': None}

    data_param_dict= {'renew': data_renew, 'rf_center': rf_center, 'local_range': local_range,\
                      'downSampleSize': 200, 'cut_data': None, \
                      'nNormalFold':3, 'nAbnormalFold':3,\
                      'handFeatures': handFeatures, 'lowVarDataRemv': False,\
                      'handFeatures_noise': True}

    save_data_path = os.path.expanduser('~')+\
      '/hrl_file_server/dpark_data/anomaly/ICRA2017/'+task+'_data/'+\
      str(data_param_dict['downSampleSize'])+'_'+str(dim)
      
    param_dict = {'data_param': data_param_dict, 'AE': AE_param_dict, 'HMM': HMM_param_dict, \
                  'SVM': SVM_param_dict, 'ROC': ROC_param_dict, 'AD': AD_param_dict}
      
    return raw_data_path, save_data_path, param_dict


def getFeeding(task, data_renew, AE_renew, HMM_renew, rf_center='kinEEPos',local_range=10.0, \
               ae_swtch=False, dim=4):

    if dim == 4:

        handFeatures = ['unimodal_audioWristRMS', 'unimodal_ftForce', \
                        'crossmodal_landmarkEEDist', 'crossmodal_landmarkEEAng']
        HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 3.5, 'scale': 4.111,\
                          'add_logp_d': True}
        ## HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 3.5, 'scale': 4.111}
        SVM_param_dict = {'renew': False, 'w_negative': 1.55, 'gamma': 4.455, 'cost': 2.25,\
                          'hmmosvm_nu': 0.000316,\
                          'osvm_nu': 0.000359,\
                          'hmmsvm_diag_w_negative': 0.2, 'hmmsvm_diag_cost': 15.0, \
                          'hmmsvm_diag_gamma': 2.0,\
                          'raw_window_size': 10,\
                          'hmmsvm_dL_w_negative': 0.525, 'hmmsvm_dL_cost': 5.0, \
                          'hmmsvm_dL_gamma': 4.0,\
                          'hmmsvm_LSLS_cost': 15.0,\
                          'hmmsvm_LSLS_gamma': 0.01, \
                          'hmmsvm_LSLS_w_negative': 1.5,
                          'bpsvm_cost': 12.5,\
                          'bpsvm_gamma': 0.01, \
                          'bpsvm_w_negative': 0.2
                          }
                          

        nPoints        = 20 
        ROC_param_dict = {'methods': ['progress_time_cluster', 'svm','fixed', 'change', 'osvm', 'hmmsvm_diag', 'hmmsvm_dL', 'hmmosvm', 'hmmsvm_LSLS', 'bpsvm' ],\
                          'update_list': ['bpsvm'],\
                          'nPoints': nPoints,\
                          'progress_param_range': -np.logspace(0., 1.2, nPoints),\
                          'svm_param_range': np.logspace(-1.8, 1.0, nPoints),\
                          'hmmsvm_diag_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmsvm_dL_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmsvm_LSLS_param_range': np.logspace(-4, 1.2, nPoints),\
                          'hmmosvm_param_range': np.logspace(-4.0, 1.0, nPoints),\
                          'change_param_range': np.logspace(0.2, 1.4, nPoints)*-1.0,\
                          'osvm_param_range': np.logspace(-5., 0.0, nPoints),\
                          'bpsvm_param_range': np.logspace(-2.2, 0.5, nPoints),\
                          'fixed_param_range': np.linspace(0.15, -0.0, nPoints),\
                          'cssvm_param_range': np.logspace(0.0, 2.0, nPoints),\
                          'sgd_param_range': np.logspace(-3, 4., nPoints)}

        AD_param_dict = {'svm_w_positive': 1.0, 'sgd_w_positive': 1.0, 'sgd_n_iter': 20}
                          
    elif dim == 3:

        handFeatures = ['unimodal_ftForce', \
                        'crossmodal_landmarkEEDist', 'crossmodal_landmarkEEAng']
        HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 3.5, 'scale': 2.555,\
                          'add_logp_d': True}
        SVM_param_dict = {'renew': False, 'w_negative': 1.55, 'gamma': 3.911, 'cost': 1.0,\
                          'hmmosvm_nu': 0.001,\
                          'hmmsvm_bpsvm_cost': 12.5,\
                          'hmmsvm_bpsvm_gamma': 0.507, \
                          'hmmsvm_bpsvm_w_negative': 0.2
                          }
                          

        nPoints        = 20 #'svm','hmmosvm'
        ROC_param_dict = {'methods': ['progress_time_cluster', 'fixed', 'svm', 'hmmosvm'],\
                          'update_list': ['hmmosvm'],\
                          'nPoints': nPoints,\
                          'progress_param_range': -np.logspace(0., 1.5, nPoints),\
                          'svm_param_range': np.logspace(-0.8, 2.5, nPoints),\
                          'bpsvm_param_range': np.logspace(-2, 0, nPoints),\
                          'hmmosvm_param_range': np.logspace(-4.5, 0.5, nPoints),\
                          'fixed_param_range': np.linspace(0.1, -0.1, nPoints),\
                          'cssvm_param_range': np.logspace(0.0, 2.0, nPoints) }

        AD_param_dict = {'svm_w_positive': 1.0, 'sgd_w_positive': 1.0}
                          
    elif dim == 2:

        ## handFeatures = ['unimodal_ftForce', \
        ##                 'crossmodal_landmarkEEDist']
        handFeatures = ['unimodal_audioWristRMS', 'unimodal_ftForce']
        HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 3.5, 'scale': 13.444,\
                          'add_logp_d': True}
        ## HMM_param_dict = {'renew': HMM_renew, 'nState': 25, 'cov': 6.0, 'scale': 3.0}
        SVM_param_dict = {'renew': False, 'w_negative': 5.0, 'gamma': 2.049, 'cost': 1.75,\
                          'hmmosvm_nu': 0.0001,\
                          'hmmsvm_bpsvm_cost': 15.0,\
                          'hmmsvm_bpsvm_gamma': 0.01, \
                          'hmmsvm_bpsvm_w_negative': 1.5
                          }

        nPoints        = 20 #, 'hmmosvm'
        ROC_param_dict = {'methods': ['progress_time_cluster', 'svm','fixed', 'hmmosvm'],\
                          'update_list': ['hmmosvm'],\
                          'nPoints': nPoints,\
                          'progress_param_range': -np.logspace(-0.3, 1.8, nPoints)+0.1,\
                          'svm_param_range': np.logspace(-2.5, 0.7, nPoints),\
                          'hmmosvm_param_range': np.logspace(-4.0, 0.5, nPoints),\
                          'fixed_param_range': np.linspace(0.5, -0.0, nPoints),\
                          'bpsvm_param_range': np.logspace(-2, 0, nPoints),\
                          'cssvm_param_range': np.logspace(0.0, 2.0, nPoints) }

        AD_param_dict = {'svm_w_positive': 1.0, 'sgd_w_positive': 1.0}

        
    rawFeatures = ['relativePose_target_EE', \
                   'wristAudio', \
                   'ft' ]
                   #'relativePose_landmark_EE', \

    modality_list   = ['ft' ,'kinematics', 'audioWrist', 'vision_landmark']
    raw_data_path  = os.path.expanduser('~')+'/hrl_file_server/dpark_data/anomaly/ICRA2017/'
    ## raw_data_path  = os.path.expanduser('~')+'/hrl_file_server/dpark_data/anomaly/RSS2016/'

    AE_param_dict  = {'renew': AE_renew, 'switch': False, 'time_window': 4, \
                      'layer_sizes':[64,dim], 'learning_rate':1e-6, 'learning_rate_decay':1e-6, \
                      'momentum':1e-6, 'dampening':1e-6, 'lambda_reg':1e-6, \
                      'max_iteration':30000, 'min_loss':0.1, 'cuda':True, \
                      'filter':True, 'filterDim':4,\
                      'add_option': None, 'rawFeatures': rawFeatures,\
                      'add_noise_option': [], 'preTrainModel': None}                      

    data_param_dict= {'renew': data_renew, 'rf_center': rf_center, 'local_range': local_range,\
                      'downSampleSize': 200, 'cut_data': None, \
                      'nNormalFold':3, 'nAbnormalFold':3,\
                      'handFeatures': handFeatures, 'lowVarDataRemv': False,\
                      'handFeatures_noise': True}

    save_data_path = os.path.expanduser('~')+\
      '/hrl_file_server/dpark_data/anomaly/ICRA2017/'+task+'_data/'+\
      str(data_param_dict['downSampleSize'])+'_'+str(dim)

    param_dict = {'data_param': data_param_dict, 'AE': AE_param_dict, 'HMM': HMM_param_dict, \
                  'SVM': SVM_param_dict, 'ROC': ROC_param_dict, 'AD': AD_param_dict}

    return raw_data_path, save_data_path, param_dict

