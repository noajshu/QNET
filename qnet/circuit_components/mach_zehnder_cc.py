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
from qnet.circuit_components.phase_cc import Phase
from qnet.circuit_components.beamsplitter_cc import Beamsplitter
from qnet.circuit_components.displace_cc import Displace


__all__ = ['MachZehnder']


class MachZehnder(Component):

    # total number of field channels
    CDIM = 2

    # parameters on which the model depends
    alpha = symbols('alpha')
    phi = symbols('phi', real = True)
    _parameters = ['alpha', 'phi']

    # list of input port names
    PORTSIN = ['a', 'b']

    # list of output port names
    PORTSOUT = ['c', 'd']

    # sub-components

    @property
    def B1(self):
        return Beamsplitter(make_namespace_string(self.name, 'B1'))

    @property
    def B2(self):
        return Beamsplitter(make_namespace_string(self.name, 'B2'))

    @property
    def P(self):
        return Phase(make_namespace_string(self.name, 'P'), phi = self.phi)

    @property
    def W(self):
        return Displace(make_namespace_string(self.name, 'W'), alpha = self.alpha)

    _sub_components = ['B1', 'B2', 'P', 'W']


    def _toSLH(self):
        return self.creduce().toSLH()

    def _creduce(self):

        B1, B2, P, W = self.B1, self.B2, self.P, self.W

        return P_sigma(1, 0) << B2 << (P + cid(1)) << P_sigma(1, 0) << B1 << (W + cid(1))

    @property
    def space(self):
        return self.creduce().space
