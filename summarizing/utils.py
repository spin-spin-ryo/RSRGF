import os
import json
import torch
import matplotlib.pyplot as plt
import numpy as np

def get_dir_from_dict(prop_dict):
    output_path = ""
    for k,v in prop_dict.items():
        output_path += k +";" +v +"_"
    return output_path[:-1]

def modify_dir_name(dir_name,global2local = True):
    change_names = [
        ("reduced_dim","reduced dim"),
        ("sample_size","sample size"),
        ("step_schedule","step schedule")
    ]
    if global2local:
        for a,b in change_names:
            dir_name = dir_name.replace(a,b)
        return dir_name
    else:
        for a,b in change_names:
            dir_name = dir_name.replace(b,a)
        return dir_name


def get_allparams_from_dir(dir_path):
    param_dirs = os.listdir(dir_path)
    default_params = {}
    for dir_name in param_dirs:
        dir_name = modify_dir_name(dir_name)
        if len(default_params) == 0:
            params = dir_name.split("_")
            for param in params:
                print(param)
                key,val = param.split(";")
                default_params[key] = [val]    
        else:
            params = dir_name.split("_")
            for param in params:
                key,val = param.split(";")
                if val not in default_params[key]:
                    default_params[key].append(val)
    return default_params

def get_params_from_dir(dir_name):
    dir_name = modify_dir_name(dir_name)
    default_params = {}
    params = dir_name.split("_")
    for param in params:
        key,val = param.split(";")
        default_params[key] = val
    return default_params    
    

def get_best_result_path(init_dir,prop_dict):
    # init_dir以下でprop_dictで指定されている要素の中から最適解のpathを見つけてくる.
    # init_dirはsolver_nameまでのdirで
    dir_list = os.listdir(init_dir)
    min_val = None
    min_val_dir = None
    for dir_name in dir_list:
        now_prop_dict = get_params_from_dir(dir_name)
        ok_flag = True
        # check
        for k,v in prop_dict.items():
            if v != "" and v != now_prop_dict[k]:
                ok_flag = False
        if ok_flag:
            if min_val is None:
                min_val = get_min_val_from_result(os.path.join(init_dir,dir_name,"result.json"))
                min_val_dir = dir_name
            else:
                now_val = get_min_val_from_result(os.path.join(init_dir,dir_name,"result.json"))
                if now_val < min_val:
                    min_val = now_val
                    min_val_dir = dir_name
    return min_val_dir,min_val


def get_min_val_from_result(file_name):
    with open(file_name) as f:
        json_dict = json.load(f)
    return json_dict["result"][0]["fvalues"]


def modify_local2global(path):
    path = path.replace(";",":")
    path = path.replace("\\","/")
    return path


def plot_result(target_pathes,*args):
    fvalues = []
    for target_path in target_pathes:
        fvalues.append(torch.load(os.path.join(target_path,"fvalues.pth")))
    
    start = 0
    end = -1
    xscale = ""
    yscale = ""
    #option関連
    for k,v in args[0].items():
        if k == "start":
            start = v
        if k == "end":
            end = v
        if k == "xscale":
            xscale = v
        if k == "yscale":
            yscale = v

    
    plt.tight_layout()
    for p,v in zip(target_pathes,fvalues):
        print(p)
        plt.plot(np.arange(len(v))[start:end],v[start:end],label = p)
    plt.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=1,borderaxespad=0)
    if xscale != "":
        plt.xscale("log")
    if yscale != "":
        plt.yscale("log")
    plt.show()
    