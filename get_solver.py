from optim_method import *
from proposed_method import *
import torch

def decreasing_stepsize(i):
    return 1/(i+1)

def decreasing_stepsize_half(i):
    return 1/((i+1)**0.5)


def get_determine_step(init_lr,step_schedule):
    if step_schedule == "constant":
        return None
    elif step_schedule == "proposed":
        return "proposed"
    elif step_schedule == "decreasing":
        determine_step = lambda i: init_lr*decreasing_stepsize(i)
        return determine_step
    elif step_schedule == "decreasing-half":
        determine_step = lambda i: init_lr*decreasing_stepsize_half(i)
        return determine_step
    else:
        raise ValueError("No step size schedule.")


def get_solver(solver_name,params_json):
    if solver_name == "GD":
        lr = float(params_json["lr"])
        solver_params = [lr]
        solver = GradientDescent()
    elif solver_name == "RGD":
        lr = float(params_json["lr"])
        reduced_dim = int(params_json["reduced_dim"])
        solver_params = [reduced_dim,lr]
        solver = SubspaceGD()
    elif solver_name == "AGD":
        lr = float(params_json["lr"])
        solver_params = [lr]
        solver = AcceleratedGD()
    elif solver_name == "RGF":
        mu = float(params_json["mu"])
        sample_size = int(params_json["sample_size"])
        lr = float(params_json["lr"])
        central = bool(params_json["central"])
        solver_params = [mu,sample_size,lr]
        step_schedule = params_json["step_schedule"]
        determine_step = get_determine_step(lr,step_schedule)
        solver = random_gradient_free(determine_step,central)
    elif solver_name == "OZD":
        mu = float(params_json["mu"])
        sample_size = int(params_json["sample_size"])
        lr = float(params_json["lr"])
        solver_params = [mu,sample_size,lr]
        step_schedule = params_json["step_schedule"]
        determine_step = get_determine_step(lr,step_schedule)
        solver = orthogonal_zeroth_order(determine_step)
    elif solver_name == "proposed":
        reduced_dim = int(params_json["reduced_dim"])
        sample_size = int(params_json["sample_size"])
        mu = float(params_json["mu"])
        lr = float(params_json["lr"])
        central = bool(params_json["central"])
        projection = bool(params_json["projection"])
        solver_params = [reduced_dim,sample_size,mu,lr]
        step_schedule = params_json["step_schedule"]
        determine_step = get_determine_step(lr,step_schedule)
        solver = proposed(determine_step,central,projection=projection)
    elif solver_name == "proposed-heuristic":
        reduced_dim = int(params_json["reduced_dim"])
        sample_size = int(params_json["sample_size"])
        mu = float(params_json["mu"])
        lr = float(params_json["lr"])
        interval = int(params_json["interval"])
        solver_params = [reduced_dim,sample_size,mu,lr,interval]
        step_schedule = params_json["step_schedule"]
        determine_step = get_determine_step(lr,step_schedule)
        solver = proposed_heuristic(determine_step)
    elif solver_name == "proposed-sparse":
        reduced_dim = int(params_json["reduced_dim"])
        sample_size = int(params_json["sample_size"])
        mu = float(params_json["mu"])
        lr = float(params_json["lr"])
        sparsity = float(params_json["sparsity"])
        solver_params = [reduced_dim,sample_size,mu,lr,sparsity]
        step_schedule = params_json["step_schedule"]
        determine_step = get_determine_step(lr,step_schedule)
        solver = proposed_sparse(determine_step)
    else:
        raise ValueError("No optimization method.")

    return solver,solver_params
