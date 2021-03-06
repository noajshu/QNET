#This file is part of QNET.
#
#    QNET is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#    QNET is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with QNET.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2012-2017, QNET authors (see AUTHORS file)
#
###########################################################################
from sympy import symbols

from qnet.circuit_components.library import make_namespace_string
from qnet.circuit_components.component import Component
from qnet.algebra.circuit_algebra import cid, P_sigma
from qnet.circuit_components.beamsplitter_cc import Beamsplitter
from qnet.circuit_components.kerr_cavity_cc import KerrCavity


__all__ = ['OpenLossy']


class OpenLossy(Component):

    # total number of field channels
    CDIM = 3

    # parameters on which the model depends
    Delta = symbols('Delta', real = True)
    chi = symbols('chi', real = True)
    kappa = symbols('kappa', real = True)
    theta = symbols('theta', real = True)
    theta_LS0 = symbols('theta_LS0', real = True)
    _parameters = ['Delta', 'chi', 'kappa', 'theta', 'theta_LS0']

    # list of input port names
    PORTSIN = ['In1']

    # list of output port names
    PORTSOUT = ['Out1', 'Out2']

    # sub-components

    @property
    def BS(self):
        return Beamsplitter(make_namespace_string(self.name, 'BS'),
                            theta=self.theta)

    @property
    def KC(self):
        return KerrCavity(make_namespace_string(self.name, 'KC'),
                          kappa_2=self.kappa, chi=self.chi,
                          kappa_1=self.kappa, Delta=self.Delta)

    @property
    def LSS_ci_ls(self):
        return Beamsplitter(make_namespace_string(self.name, 'LSS'),
                            theta=self.theta_LS0)

    _sub_components = ['BS', 'KC', 'LSS_ci_ls']


    def _toSLH(self):
        return self.creduce().toSLH()

    def _creduce(self):

        BS, KC, LSS_ci_ls = self.BS, self.KC, self.LSS_ci_ls

        return (KC + cid(1)) << P_sigma(0, 2, 1) << (LSS_ci_ls + cid(1)) << P_sigma(0, 2, 1) << (BS + cid(1))

    @property
    def space(self):
        return self.creduce().space
