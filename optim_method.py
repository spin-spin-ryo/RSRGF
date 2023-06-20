import torch
import matplotlib.pyplot as plt
import numpy as np
import os
from torch.autograd.functional import hessian
from utils import GetMinimumEig,compute_hvp

SAVEPATH = "./results"


class __optim__:
    def __init__(self):
        self.xk = None
        self.params = None
        self.fvalues = None
        self.loss = None
        self.func = None
        self.device = None
        return

    def __direction__(self):
        return 

    def __update__(self,dk):
        with torch.no_grad():
            self.xk += dk
        return

    def __clear__(self):
        self.xk.grad = None
        return
    
    def __set__(self,loss):
        self.loss = loss
        return
    
    def __iter__(self,func,x0,params,iterations):
        self.params = params
        self.xk = x0
        self.func = func
        self.fvalues = torch.zeros(iterations)
        for i in range(iterations):
            self.__clear__()
            loss = self.func(self.xk)
            self.fvalues[i] = loss.item()
            self.__set__(loss)
            dk = self.__direction__()
            self.__update__(dk)

    def __plot__(self):
        plt.plot(np.arange(len(self.fvalues)),self.fvalues)
        plt.savefig(os.path.join(SAVEPATH,"fvalues.png"))
        plt.close()
    
class GradientDescent(__optim__):
    #固定ステップサイズのGD
    def __init__(self):
        super().__init__()
    
    def __direction__(self):
        self.loss.backward()
        return self.xk.grad

    def __update__(self, dk):
        # step sizeを求める
        lr = self.params
        return super().__update__(lr*dk)        

    def __iter__(self, func, x0, lr, iterations):
        return super().__iter__(func, x0, lr, iterations)

class SubspaceGD(__optim__):
    def __init__(self):
        super().__init__()
    
    def __direction__(self):
        reduced_dim = self.params[0]
        dim = self.xk.shape[0]
        P = torch.randn(reduced_dim,dim)/(dim**(0.5))
        P = P.to(self.device)
        self.loss.backward()
        return - P.transpose(0,1)@P@self.xk.grad

    def __update__(self, dk):
        lr = self.params[1]
        return super().__update__(lr*dk)        

class AcceleratedGD(__optim__):
    def __init__(self):
        self.yk = None
        self.lambda_k = 0
        super().__init__()

    def __iter__(self, func, x0, params, iterations):
        self.yk = x0.clone().detach()
        return super().__iter__(func, x0, params, iterations)    

    def __direction__(self):
        lr = self.params[0]
        self.loss.backward()
        with torch.no_grad():
            yk1 = self.xk - lr*self.xk.grad
            return yk1
    
    def __update__(self, yk1):
        lambda_k1 = (1 + (1 + 4*self.lambda_k**2)**(0.5))/2
        gamma_k = ( 1 - self.lambda_k)/lambda_k1
        with torch.no_grad():
            self.xk = (1 - gamma_k)*yk1 + gamma_k*self.yk
            self.yk = yk1
            self.lambda_k = lambda_k1
            return 

class NewtonMethod(__optim__):
    def __init__(self):
        super().__init__()
    
    def __direction__(self):
        H = hessian(self.func,self.xk)
        self.loss.backward()
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
    
    def __direction__(self):
        reduced_dim = self.params[0]
        dim = self.xk.shape[0]
        self.Pk = torch.randn(dim,reduced_dim)/(dim**0.5)
        self.Pk = self.Pk.to(self.device)
        d = torch.zeros(reduced_dim).to(self.device)
        PHP = hessian(self.subspace_func,d)
        self.loss.backward()
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
    
    def __direction__(self):
        reduced_dim = self.params[0]
        c1 = self.params[1]
        c2 = self.params[2]
        r = self.params[3]
        dim = self.xk.shape[0]

        self.Pk = torch.randn(dim,reduced_dim)/(dim**0.5)
        self.Pk = self.Pk.to(self.device)
        d = torch.zeros(reduced_dim).to(self.device)
        PHP = hessian(self.subspace_func,d)
        self.loss.backward()
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
    
    def __direction__(self):
        c1 = self.params[0]
        c2 = self.params[1]
        r = self.params[2]
        dim = self.xk.shape[0]
        H = hessian(self.func,self.xk)
        self.loss.backward()
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