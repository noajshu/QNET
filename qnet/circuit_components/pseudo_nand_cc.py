#!/usr/bin/env python
# encoding: utf-8
from sympy import symbols

from qnet.circuit_components.library import make_namespace_string
from qnet.circuit_components.component import Component
from qnet.algebra.circuit_algebra import cid, P_sigma, FB
from qnet.circuit_components.kerr_cavity_cc import KerrCavity
from qnet.circuit_components.phase_cc import Phase
from qnet.circuit_components.beamsplitter_cc import Beamsplitter
from qnet.circuit_components.displace_cc import Displace


__all__ = ['PseudoNAND']


class PseudoNAND(Component):

    # total number of field channels
    CDIM = 4

    # parameters on which the model depends
    Delta = symbols('Delta', real = True)
    chi = symbols('chi', real = True)
    kappa = symbols('kappa', real = True)
    phi = symbols('phi', real = True)
    theta = symbols('theta', real = True)
    beta = symbols('beta')
    _parameters = ['Delta', 'beta', 'chi', 'kappa', 'phi', 'theta']

    # list of input port names
    PORTSIN = ['A', 'B', 'VIn1', 'VIn2']

    # list of output port names
    PORTSOUT = ['UOut1', 'UOut2', 'NAND_AB', 'OUT2']

    # sub-components

    @property
    def BS1(self):
        return Beamsplitter(make_namespace_string(self.name, 'BS1'))

    @property
    def BS2(self):
        return Beamsplitter(make_namespace_string(self.name, 'BS2'), theta = self.theta)

    @property
    def K(self):
        return KerrCavity(make_namespace_string(self.name, 'K'), kappa_2 = self.kappa, chi = self.chi, kappa_1 = self.kappa, Delta = self.Delta)

    @property
    def P(self):
        return Phase(make_namespace_string(self.name, 'P'), phi = self.phi)

    @property
    def W_beta(self):
        return Displace(make_namespace_string(self.name, 'W'), alpha = self.beta)

    _sub_components = ['BS1', 'BS2', 'K', 'P', 'W_beta']


    def _toSLH(self):
        return self.creduce().toSLH()

    def _creduce(self):

        BS1, BS2, K, P, W_beta = self.BS1, self.BS2, self.K, self.P, self.W_beta

        return (cid(1) + ((cid(1) + ((P + cid(1)) << BS2 << (W_beta + cid(1)))) << P_sigma(0, 2, 1) << (K + cid(1)))) << (BS1 + cid(2)) << P_sigma(0, 1, 3, 2)

    @property
    def space(self):
        return self.creduce().space
