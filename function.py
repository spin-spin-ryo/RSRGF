from typing import Any
import torch
import torch.nn as nn
import torch.nn.functional as F

class Function:
  def __init__(self,params = []):
    self.params = params
    return

  def __call__(self,x):
    return
  
  def SetDtype(self,dtype):
    for i in range(len(self.params)):
      if self.params[i] is not None:
        self.params[i] = self.params[i].to(dtype)
    return
  def SetDevice(self,device):
    for i in range(len(self.params)):
      if self.params[i] is not None:
        self.params[i] = self.params[i].to(device)
    return

class QuadraticFunction(Function):
  def __call__(self,x):
    Q = self.params[0]
    b = self.params[1]
    return 1/2*(Q@x)@x+b@x

class test_function(Function):
  def __call__(self,x):
    return 1/2*x@x

class max_linear(Function):
  def __call__(self, x):
    A = self.params[0]
    b = self.params[1]
    return torch.max(A@x + b)

class piecewise_linear(Function):
  def __call__(self,x):
    return torch.abs(1-x[0]) + torch.sum(torch.abs( 1 + x[1:] - 2*x[:-1]))
  
class norm_function(Function):
  def __call__(self, x):
    Q = self.params[0]
    b = self.params[1]
    p = self.params[2]
    return torch.linalg.norm(Q@x - b,ord = p)

class logistic(Function):
  def __call__(self,x):
    X = self.params[0]
    y = self.params[1]
    a = X@x
    return torch.mean(torch.log(1 + torch.exp(-y*a)))

class subspace_norm(Function):
  def __call__(self,x):
    r = self.params[0]
    p = self.params[1]
    return torch.linalg.norm(x[:r],ord = p)**p
  
  def SetDtype(self,dtype):
    for i in range(len(self.params)):
      if self.params[i] is not None:
        self.params[i] = self.params[i].to(torch.int64)
    return  

class rosenbrock(Function):
  def __call__(self,x):
    super().__call__(x)

class regularizedfunction(Function):
  def __init__(self,f,params):
    self.f = f
    assert len(params) ==3
    self.params = params
    return

  def __call__(self,x):
    p = self.params[-3]
    l = self.params[-2]
    A = self.params[-1]
    if A is not None:
      return self.f(x) + l*torch.linalg.norm(A@x,ord = p)
    else:
      return self.f(x) + l*torch.linalg.norm(x,ord = p)
  
  def SetDevice(self, device):
    self.f.SetDevice(device)
    return super().SetDevice(device)

  def SetDtype(self, dtype):
    self.f.SetDtype(dtype)
    return super().SetDtype(dtype)

class CNN_func(Function):
    def __init__(self, params):
      super().__init__(params)
      self.criterion = nn.CrossEntropyLoss()

    def __call__(self,x):
      params = 0
      weight1 = x[params:params + 16*1*5*5].reshape(16,1,5,5)
      params += 16*1*5*5
      bias1 = x[params:params+16]
      params += 16
      weight2 = x[params:params + 32*16*5*5].reshape(32,16,5,5)
      params += 32*16*5*5
      bias2 = x[params:params + 32]
      params += 32
      W = x[params:params + 8 * 8 * 32 *10].reshape(10,8 * 8 * 32)
      params += 8 * 8 * 32 *10
      b = x[params:]
      params += 10

      z = F.conv2d(input = self.params[0],weight = weight1, bias = bias1,padding = 2)
      z = torch.sigmoid(z)
      z = F.avg_pool2d(input = z , kernel_size= 2)
      z = F.conv2d(input = z, weight = weight2, bias = bias2,padding =2)
      z = torch.sigmoid(z)
      z = F.avg_pool2d(input = z,kernel_size = 2)
      z = z.view(z.size(0), -1)
      z = F.linear(z, W, bias=b)
      return self.criterion(z, self.params[1].to(torch.int64))

    def predict(self,x):
      params = 0
      weight1 = x[params:params + 16*1*5*5].reshape(16,1,5,5)
      params += 16*1*5*5
      bias1 = x[params:params+16]
      params += 16
      weight2 = x[params:params + 32*16*5*5].reshape(32,16,5,5)
      params += 32*16*5*5
      bias2 = x[params:params + 32]
      params += 32
      W = x[params:params + 8 * 8 * 32 *10].reshape(10,8 * 8 * 32)
      params += 8 * 8 * 32 *10
      b = x[params:]
      params += 10

      z = F.conv2d(input = self.params[0],weight = weight1, bias = bias1,padding = 2)
      z = torch.sigmoid(z)
      z = F.avg_pool2d(input = z , kernel_size= 2)
      z = F.conv2d(input = z, weight = weight2, bias = bias2,padding =2)
      z = torch.sigmoid(z)
      z = F.avg_pool2d(input = z,kernel_size = 2)
      z = z.view(z.size(0), -1)
      z = F.linear(z, W, bias=b)
      return torch.argmax(z,dim = 1)

