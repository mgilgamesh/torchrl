import numpy as np

import torch
import torch.optim as optim
import torch.nn as nn

from .on_rl_algo import OnRLAlgo

class A2C(OnRLAlgo):
    """
    Actor Critic
    """
    def __init__(
        self,
        pf, vf, 
        plr = 3e-4,
        vlr = 3e-4,
        optimizer_class=optim.Adam,
        entropy_coeff = 0.001,
        **kwargs
    ):
        super(A2C, self).__init__(**kwargs)
        self.pf = pf
        self.vf = vf
        self.to(self.device)

        self.plr = plr
        self.vlr = vlr

        self.pf_optimizer = optimizer_class(
            self.pf.parameters(),
            lr=self.plr,
            weight_decay=0.002
        )

        self.vf_optimizer = optimizer_class(
            self.vf.parameters(),
            lr=self.vlr,
            weight_decay=0.002
        )

        self.entropy_coeff = entropy_coeff
        
        self.vf_criterion = nn.MSELoss()
    
    def update(self, batch):
        self.training_update_num += 1

        info = {}

        obs = batch['obs']
        acts = batch['acts']
        advs = batch['advs']
        est_rets = batch['estimate_returns']
        
        assert len(advs.shape) == 2
        assert len(est_rets.shape) == 2

        obs = torch.Tensor(obs).to( self.device )
        acts = torch.Tensor(acts).to( self.device )
        advs = torch.Tensor(advs).to( self.device )
        est_rets = torch.Tensor(est_rets).to( self.device )

        out = self.pf.update( obs, acts )
        log_probs = out['log_prob']
        ent = out['ent']

        assert log_probs.shape == advs.shape

        policy_loss = -log_probs * advs
        policy_loss = policy_loss.mean() - self.entropy_coeff * ent.mean()

        values = self.vf(obs)
        vf_loss = self.vf_criterion( values, est_rets )

        self.pf_optimizer.zero_grad()
        policy_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.pf.parameters(), 0.5)
        self.pf_optimizer.step()

        self.vf_optimizer.zero_grad()
        vf_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.vf.parameters(), 0.5)
        self.vf_optimizer.step()

        info['Traning/policy_loss'] = policy_loss.item()
        info['Traning/vf_loss'] = vf_loss.item()

        
        info['v_pred/mean'] = values.mean().item()
        info['v_pred/std'] = values.std().item()
        info['v_pred/max'] = values.max().item()
        info['v_pred/min'] = values.min().item()

        info['ent'] = ent.mean().item()
        info['log_prob'] = log_probs.mean().item()

        return info
