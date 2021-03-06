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

"""
Component definition file for a degenerate OPO model with two signal beam ports.
See documentation of :py:class:`DoubleSidedOPO`.
"""
from sympy.core.symbol import symbols
from sympy import I, sqrt

from qnet.algebra.circuit_algebra import SLH
from qnet.algebra.matrix_algebra import Matrix, identity_matrix
from qnet.algebra.operator_algebra import Destroy
from qnet.algebra.hilbert_space_algebra import LocalSpace
from qnet.circuit_components.component import Component, SubComponent


__all__ = ["DoubleSidedOPO"]


class DoubleSidedOPO(Component):
    r"""This model describes a degenerate OPO with two signal beam ports in the
    sub-threshold regime. I.e., the pump is modeled as a classical amplitude.

    The model's SLH parameters are given by

    .. math::
        S & = \mathbf{1}_2 \\
        L & = \begin{pmatrix} \sqrt{\kappa_1} a \\ \sqrt{\kappa_2} a \end{pmatrix} \\
        H &= \Delta a^\dagger a + {i\over 2} \left( \alpha {a^\dagger}^2 - \alpha^* a^2\right)

    This particular component definition explicitly captures the reducibility of a trivial scattering matrix.
    I.e., it can be reduced into separate :py:class:`OPOPort` models for each port.


    Note that this model's validity breaks down even in open-loop configuration when

    .. math::
        |\alpha| > {\kappa_1 + \kappa_2 \over 2}

    which is just the threshold condition.
    In a feedback configuration the threshold condition is generally changed.
    """

    CDIM = 2

    kappa_1 = symbols('kappa_1', real = True) # decay of cavity mode through cavity mirror
    kappa_2 = symbols('kappa_2', real = True) # decay rate into transverse modes
    alpha = symbols('alpha')   # coupling between cavity mode and two-level-system
    Delta = symbols('Delta', real = True) # detuning between the cavity (mode) and the atomic transition
    FOCK_DIM = 25
    _parameters = ['kappa_1', 'kappa_2', 'alpha', 'Delta', 'FOCK_DIM']


    PORTSIN = ['In1', 'In2']
    PORTSOUT = ['Out1', 'Out2']

    sub_blockstructure = (1, 1)

    @property
    def space(self):
        return LocalSpace(self.name, dimension=self.FOCK_DIM)

    def _creduce(self):
        return OPOPort(self, 0) + OPOPort(self, 1)

    def _toSLH(self):
        return self.creduce().toSLH()


class OPOPort(SubComponent):
    """Sub component model for the individual ports of a
    :py:class:`DoubleSidedOPO`.  The Hamiltonian is included with the first
    port."""

    def _toSLH(self):

        a = Destroy(hs=self.space)
        a_d = a.adjoint()

        S = identity_matrix(1)

        if self.sub_index == 0:
            # Include the Hamiltonian only with the first port of the kerr cavity circuit object
            H = self.Delta * a_d * a + (I/2) * (self.alpha * a_d * a_d - self.alpha.conjugate() * a * a)
            L = Matrix([[sqrt(self.kappa_1) * a]])
        else:
            H = 0
            L = Matrix([[sqrt(self.kappa_2) * a]])

        return SLH(S, L, H)
