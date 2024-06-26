import torch
import matplotlib.pyplot as plt
import numpy as np
import os
from utils import GetMinimumEig,compute_hvp,generate_sub_orthogonal
import time
import json
from environments import *
from torch.autograd.functional import hessian
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

class __optim__:
    def __init__(self):
        self.xk = None
        self.params = None
        self.save_values = {}
        self.func = None
        self.device = None
        self.dtype = None
        self.start_time = None
        self.loss_time = 0
        return

    def __direction__(self,loss):
        return

    def __update__(self,dk):
        with torch.no_grad():
            self.xk += dk
        return

    def __clear__(self):
        self.xk.grad = None
        return
    
    def __log__(self,iteration):
        min_val = torch.min(self.save_values[("fvalues","min")][:iteration])
        time_val = self.save_values[("time_values","max")][iteration]
        logger.info(f"{iteration + 1}")
        logger.info(f"min_value:{min_val}")
        logger.info(f"time:{time_val}")
    
    
    def __iter_per__(self,i):
        self.__clear__()
        torch.cuda.synchronize()
        loss_start_time = time.time()
        loss = self.func(self.xk)
        torch.cuda.synchronize()
        self.loss_time += time.time() - loss_start_time
        dk = self.__direction__(loss)
        lr = self.__step__(i)
        self.__update__(lr*dk)
        torch.cuda.synchronize()
        self.__save_value__(i,fvalues = ("min",loss.item()),time_values = ("max",time.time() - self.loss_time - self.start_time))
        return
    
    def __step__(self,i):
        return 1.0
    
    def __iter__(self,func,x0,params,iterations,savepath,suffix = "",interval = None):
        if interval is None:
            interval = iterations
        torch.cuda.synchronize()
        self.start_time = time.time()
        self.params = params
        self.xk = x0
        self.func = func
        self.__save_init__(iterations,fvalues = "min",time_values = "max")
        for i in range(iterations):
            self.__iter_per__(i)
            if (i+1)%interval == 0:
                self.__save__(savepath,suffix=suffix,fvalues = "min",time_values = "max")
                self.__log__(i)
    
    def __save_init__(self,iterations,**kwargs):
        for key,ope in kwargs.items():
            self.save_values[(key,ope)] = torch.zeros(iterations,dtype = DTYPE)
            
    def __save_value__(self,index, **kwargs):
        for key,t in kwargs.items():
            ope = t[0]
            value = t[1]
            self.save_values[(key,ope)][index] = value
            
    
    def __save__(self,savepath,suffix = "",**kwargs):
        for key,ope in kwargs.items():
            torch.save(self.save_values[(key,ope)],os.path.join(savepath,key + f"{suffix}.pth"))
        return
        

    
    

"""
first and second order method
"""

class GradientDescent(__optim__):
    #固定ステップサイズのGD
    def __init__(self):
        # params = [lr]
        self.grad_value = None
        super().__init__()
    
    def __direction__(self,loss):
        loss.backward()
        return - self.xk.grad

    def __update__(self, dk):
        # step sizeを求める
        lr = self.params[0]
        return super().__update__(lr*dk)
    
    def __save_init__(self, iterations, **kwargs):
        self.save_values[("grad_values","min")] = torch.zeros(iterations,dtype = DTYPE)
        return super().__save_init__(iterations, **kwargs)
    
    def __save_value__(self, index, **kwargs):
        self.save_values[("grad_values","min")][index] = torch.linalg.norm(self.xk.grad).item()
        return super().__save_value__(index, **kwargs)
        

class SubspaceGD(__optim__):
    def __init__(self):
        # params = [reduced_dim,lr]
        super().__init__()
    
    def __direction__(self,loss):
        reduced_dim = self.params[0]
        dim = self.xk.shape[0]
        P = torch.randn(reduced_dim,dim)/(reduced_dim**(0.5))
        P = P.to(self.device).to(self.dtype)
        loss.backward()
        return - P.transpose(0,1)@P@self.xk.grad

    def __update__(self, dk):
        lr = self.params[1]
        return super().__update__(lr*dk)  

    def __save_init__(self, iterations,**kwargs):
        self.save_values[("grad_values","min")] = torch.zeros(iterations,dtype = DTYPE)
        return super().__save_init__(iterations,**kwargs)

    def __save_value__(self,index,**kwargs):
        self.save_values[("grad_values","min")][index] = torch.linalg.norm(self.xk.grad).item()
        return super().__save_value__(index,**kwargs)      

class AcceleratedGD(__optim__):
    def __init__(self):
        self.yk = None
        self.lambda_k = 0
        super().__init__()

    def __iter__(self, func,x0,params,iterations,savepath,interval = None):
        self.yk = x0.clone().detach()
        return super().__iter__(func,x0,params,iterations,savepath,interval)    

    def __direction__(self,loss):
        loss.backward()
        return self.xk.grad
        
    def __update__(self, grad):
        lr = self.params[0]
        lambda_k1 = (1 + (1 + 4*self.lambda_k**2)**(0.5))/2
        gamma_k = ( 1 - self.lambda_k)/lambda_k1
        with torch.no_grad():
            yk1 = self.xk - lr*grad
            self.xk = (1 - gamma_k)*yk1 + gamma_k*self.yk
            self.yk = yk1
            self.lambda_k = lambda_k1
        self.xk.requires_grad_(True)
        self.xk.grad = grad
        return
    
    def __save_init__(self, iterations,**kwargs):
        self.save_values[("grad_values","min")] = torch.zeros(iterations,dtype = DTYPE)
        return super().__save_init__(iterations,**kwargs)

    def __save_value__(self, index,**kwargs):
        self.save_values[("grad_values","min")][index] = torch.linalg.norm(self.xk.grad).item()
        return super().__save_value__(index,**kwargs)




"""
zeroth order method
"""

class random_gradient_free(__optim__):
    #　directionの計算を同時にやることで削減する方法もありそうだがとりあえずfor 文
    def __init__(self,determine_stepsize = None,central = False):
        # params = [mu,sample_size,lr]
        self.determine_stepsize  = determine_stepsize
        self.central = central
        super().__init__()
        print("central",self.central)

    def __direction__(self,loss):
        mu = self.params[0]
        sample_size = self.params[1]
        dim = self.xk.shape[0]
        dir = None
        P = torch.randn(sample_size,dim,device = self.device,dtype = self.dtype)/(sample_size**(0.5))
        for i in range(sample_size):
            if self.central:
                f1 = self.func(self.xk + mu*P[i])
                f2 = self.func(self.xk - mu*P[i])
                if dir is None:
                    dir = (f1.item() - f2.item())/(2*mu) *P[i]
                else:
                    dir += (f1.item() - f2.item())/(2*mu) *P[i]
            else:
                f1 = self.func(self.xk + mu*P[i])
                if dir is None:
                    dir = (f1.item() - loss.item())/mu * P[i] 
                else:
                    dir += (f1.item() - loss.item())/mu * P[i]
        return - dir 
    
    def __step__(self,i):
        if self.determine_stepsize is not None:
            return self.determine_stepsize(i);
        else:
            lr = self.params[2]
            return lr
    
    def __iter_per__(self, i):
        return super().__iter_per__(i)

    def __save_init__(self, iterations, **kwargs):
        self.xk.requires_grad_(False)
        return super().__save_init__(iterations, **kwargs)
    
class orthogonal_zeroth_order(__optim__):
    def __init__(self,determine_stepsize = None):
        # params = [mu,sample_size,lr]
        self.determine_stepsize  = determine_stepsize
        super().__init__()
        
    def __direction__(self,loss):
        with torch.no_grad():
            mu = self.params[0]
            sample_size = self.params[1]
            dim = self.xk.shape[0]
            dir = None
            P = generate_sub_orthogonal(sample_size,dim)
            for i in range(sample_size):
                f1 = self.func(self.xk + mu*P[i])
                f2 = self.func(self.xk - mu*P[i])
                if dir is None:
                    dir = (f1.item() - f2.item())/(2*mu) *P[i]
                else:
                    dir += (f1.item() - f2.item())/(2*mu) *P[i]
            return - dim*dir 
    
    def __step__(self,i):
        if self.determine_stepsize is not None:
            return self.determine_stepsize(i);
        else:
            lr = self.params[2]
            return lr
    
    def __iter_per__(self, i):
        with torch.no_grad():
            return super().__iter_per__(i)




"""
second order method
"""
    
class NewtonMethod(__optim__):
    def __init__(self):
        super().__init__()
    
    def __direction__(self,loss):
        H = hessian(self.func,self.xk)
        loss.backward()
        return - torch.linalg.solve(H,self.xk.grad)
    
    def __update__(self, dk):
        alpha = self.params[0]
        beta = self.params[1]
        lr = 1
        with torch.no_grad():
            while self.loss.item() - self.func(self.xk + lr*dk) < -alpha*lr*self.xk.grad@dk:
                lr *= beta  
        return super().__update__(lr*dk)

class SubspaceNewton(__optim__):
    def __init__(self):
        self.Pk = None
        super().__init__()
    
    def subspace_func(self,d):
        return self.func(self.xk + self.Pk@d)
    
    def __direction__(self,loss):
        reduced_dim = self.params[0]
        dim = self.xk.shape[0]
        self.Pk = torch.randn(dim,reduced_dim)/(dim**0.5)
        self.Pk = self.Pk.to(self.device)
        d = torch.zeros(reduced_dim).to(self.device)
        PHP = hessian(self.subspace_func,d)
        loss.backward()
        return - self.Pk @ torch.linalg.solve(PHP,self.Pk.transpose(0,1)@self.xk.grad)
    
    def __update__(self, dk):
        alpha = self.params[1]
        beta = self.params[2]
        lr = 1
        with torch.no_grad():
            while self.loss.item() - self.func(self.xk + lr*dk) < -alpha*lr*self.xk.grad@dk:
                lr *= beta  
        return super().__update__(lr*dk)

class SubspaceRNM(__optim__):
    def __init__(self):
        super().__init__()
    
    def subspace_func(self,d):
        return self.func(self.xk + self.Pk@d)
    
    def __direction__(self,loss):
        reduced_dim = self.params[0]
        c1 = self.params[1]
        c2 = self.params[2]
        r = self.params[3]
        dim = self.xk.shape[0]

        self.Pk = torch.randn(dim,reduced_dim)/(dim**0.5)
        self.Pk = self.Pk.to(self.device)
        d = torch.zeros(reduced_dim).to(self.device)
        PHP = hessian(self.subspace_func,d)
        loss.backward()
        min_eig = GetMinimumEig(PHP)
        Lambda_k = max(0,-min_eig)
        Mk = PHP + c1*Lambda_k*torch.eye(reduced_dim,device = self.device) + c2 * torch.linalg.norm(self.xk.grad)**r * torch.eye(reduced_dim,device= self.device)
        return - self.Pk@ torch.linalg.solve(Mk, self.Pk.transpose(0,1)@self.xk.grad)
    
    def __update__(self, dk):
        alpha = self.params[4]
        beta = self.params[5]
        lr = 1
        with torch.no_grad():
            while self.loss.item() - self.func(self.xk + lr*dk) < -alpha*lr*self.xk.grad@dk:
                lr *= beta  
        return super().__update__(lr*dk)

class ExtendedRMM(__optim__):
    def __init__(self):
        super().__init__()
    
    def __direction__(self,loss):
        c1 = self.params[0]
        c2 = self.params[1]
        r = self.params[2]
        dim = self.xk.shape[0]
        H = hessian(self.func,self.xk)
        loss.backward()
        min_eig = GetMinimumEig(H)
        Lambda_k = max(0,-min_eig)
        Mk = H + c1*Lambda_k*torch.eye(dim,device = self.device) + c2 * torch.linalg.norm(self.xk.grad)**r * torch.eye(dim,device= self.device)
        return - torch.linalg.solve(Mk, self.xk.grad)
    
    def __update__(self, dk):
        alpha = self.params[3]
        beta = self.params[4]
        lr = 1
        with torch.no_grad():
            while self.loss.item() - self.func(self.xk + lr*dk) < -alpha*lr*self.xk.grad@dk:
                lr *= beta  
        return super().__update__(lr*dk)
    
    


# class NewtonCG(__optim__):
#     def __init__(self):
#         super().__init__()
    
#     def update_parameters(self,M,e,l):
#         k = (M + 2*e)/e
#         le = l/3/k
#         t = k**0.5/(k**0.5 + 1)
#         T = 4*k**4 / (1 - t**0.5)**2
#         return k,le,t,T

    
#     def CCG(self,g,e,l,M = 0):
#         k = (M + 2*e)/e
#         le = l/3/k
#         t = k**0.5/(k**0.5 + 1)
#         T = 4*k**4 / (1 - t**0.5)**2

#         y = torch.zeros(g.shape[0],device = self.device)
#         ys = [y]
#         Hys = [y]
#         r = g
#         p = -g
#         Hp = compute_hvp(self.func,self.xk,p)
#         if p@Hp < - e*p@p:
#             return p,"NC"
        
#         if torch.linalg.norm(Hp) > M*torch.linalg.norm(p):
#             M = torch.linalg.norm(Hp)/torch.linalg.norm(p)
#             k,le,t,T = self.update_parameters(M,e,l)
#         j = 0
#         while True:
#             alpha = (r@r)/(p@Hp + 2*e * p@p)
#             y1 = y + alpha*p
#             r1 = r + alpha*Hp
#             beta = (r1@r1)/(r@r)
#             p1 = -r1 + beta*p
#             j += 1
#             Hp1 = compute_hvp(self.func,self.xk,p1)
#             if torch.linalg.norm(Hp1) > M*torch.linalg.norm(p1):
#                 M = torch.linalg.norm(Hp1)/torch.linalg.norm(p1)
#                 k,le,t,T = self.update_parameters(M,e,l)
#             Hy1 = compute_hvp(self.func,self.xk,y1)
#             if torch.linalg.norm(Hy1) > M*torch.linalg.norm(y1):
#                 M = torch.linalg.norm(Hy1)/torch.linalg.norm(y1)
#                 k,le,t,T = self.update_parameters(M,e,l)
#             Hr1 = compute_hvp(self.func,self.xk,r1)
#             if torch.linalg.norm(Hr1) > M*torch.linalg.norm(r1):
#                 M = torch.linalg.norm(Hr1)/torch.linalg.norm(r1)
#                 k,le,t,T = self.update_parameters(M,e,l)
            
#             ys.append(y1)
#             Hys.append(Hy1)
            
#             if y1@Hr1 < -e*y1@y1:
#                 return y1,"NC"
#             if torch.linalg.norm(r1) < le*torch.linalg.norm(g):
#                 return y1,"SOL"
#             if p1@Hp1 < -e*p1@p1:
#                 return p1,"NC"
#             if torch.linalg.norm(r1) > T**0.5 * t**(j/2) * torch.linalg.norm(g):
#                 alpha =r1@r1/(p1@Hp1 + 2*e * p1@p1 )
#                 y2 = y1 + alpha*p1

#             r = r1
#             p = p1
#             y = y1

#     def Lanczes
