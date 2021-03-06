# This file is part of QNET.
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

import os

import pytest

from qnet.misc.testing_tools import datadir
from qnet.algebra.circuit_algebra import (
    cid, P_sigma, FB, SeriesProduct, Feedback, CPermutation, Concatenation,
    CIdentity)
from qnet.circuit_components.beamsplitter_cc import Beamsplitter
from qnet.circuit_components.three_port_kerr_cavity_cc import (
    ThreePortKerrCavity)
from qnet.circuit_components.phase_cc import Phase
from qnet.circuit_components.displace_cc import Displace
from qnet.printing.srepr import srepr, IndentedSReprPrinter
from qnet.printing.unicode import unicode, UnicodePrinter
from qnet.printing import configure_printing


datadir = pytest.fixture(datadir)


def test_latch_srepr(datadir):
    """Test rendering of the "Latch" circuit component creduce expression"""
    # There is a problem with Components being cached incorrectly, so we have
    # to clear the instance cache until this is fixed
    IndentedSReprPrinter.clear_registry()
    B11 = Beamsplitter('Latch.B11')
    B12 = Beamsplitter('Latch.B12')
    B21 = Beamsplitter('Latch.B21')
    B22 = Beamsplitter('Latch.B22')
    B3 = Beamsplitter('Latch.B3')
    C1 = ThreePortKerrCavity('Latch.C1')
    C2 = ThreePortKerrCavity('Latch.C2')
    Phase1 = Phase('Latch.Phase1')
    Phase2 = Phase('Latch.Phase2')
    Phase3 = Phase('Latch.Phase3')
    W1 = Displace('Latch.W1')
    W2 = Displace('Latch.W2')
    IndentedSReprPrinter.register(B11, 'B11')
    registry = {
         B12: 'B12', B21: 'B21', B22: 'B22', B3: 'B3', C1: 'C1', C2: 'C2',
         Phase1: 'Phase1', Phase2: 'Phase2', Phase3: 'Phase3', W1: 'W1',
         W2: 'W2'}
    IndentedSReprPrinter.update_registry(registry)
    registry[B11] = 'B11'
    # from qnet.circuit_components.latch_cc.Latch
    expr = (
        P_sigma(1, 2, 3, 4, 5, 6, 7, 0) <<
        FB(((cid(4) + (P_sigma(0, 4, 1, 2, 3) << (B11 + cid(3)))) <<
            P_sigma(0, 1, 2, 3, 4, 6, 7, 8, 5) <<
            ((P_sigma(0, 1, 2, 3, 4, 7, 5, 6) <<
             ((P_sigma(0, 1, 5, 3, 4, 2) <<
              FB((cid(2) +
                  ((B3 + cid(1)) <<
                      P_sigma(0, 2, 1) <<
                      (B12 + cid(1))) +
                  cid(2)) <<
                  P_sigma(0, 1, 4, 5, 6, 2, 3) <<
                  (((cid(1) +
                      ((cid(1) + ((Phase3 + Phase2) << B22) + cid(1)) <<
                       P_sigma(0, 1, 3, 2) << (C2 + W2))) <<
                      ((B21 << (Phase1 + cid(1))) + cid(3))) +
                   cid(2)),
                  out_port=4, in_port=0)) +
              cid(2)) <<
             (cid(4) +
             (P_sigma(0, 2, 3, 1) << ((P_sigma(1, 0, 2) << C1) + W1)))) +
             cid(1))), out_port=8, in_port=4) <<
        P_sigma(7, 0, 6, 3, 1, 2, 4, 5))
    rendered = srepr(expr, indented=True)
    # the rendered expression is directly the Python code for a more efficient
    # evaluation of the same expression
    with open(os.path.join(datadir, 'latch_srepr.dat')) as in_fh:
        expected = in_fh.read().strip()
    assert rendered == expected
    assert eval(rendered) == expr
    IndentedSReprPrinter.clear_registry()

    UnicodePrinter.clear_registry()
    with configure_printing(cached_rendering=False):
        expected = (
            r'Perm(1, 2, 3, 4, 5, 6, 7, 0) ◁ [(cid(4) ⊞ Perm(0, 4, 1, 2, 3) '
            r'◁ (Latch.B11)) ◁ Perm(0, 1, 2, 3, 4, 6, 7, 8, 5) ◁ '
            r'(Perm(0, 1, 2, 3, 4, 7, 5, 6) ◁ (Perm(0, 1, 5, 3, 4, 2) ◁ '
            r'[(cid(2) ⊞ (Latch.B3) ◁ Perm(0, 2, 1) ◁ (Latch.B12)) ◁ '
            r'Perm(0, 1, 4, 5, 6, 2, 3) ◁ ((cid(1) ⊞ (cid(1) ⊞ (Latch.Phase3 '
            r'⊞ Latch.Phase2) ◁ Latch.B22) ◁ Perm(0, 1, 3, 2) ◁ (Latch.C2 ⊞ '
            r'Latch.W2(α))) ◁ (Latch.B21 ◁ (Latch.Phase1)))]₄₋₀) ◁ (cid(4) ⊞ '
            r'Perm(0, 2, 3, 1) ◁ (Perm(1, 0, 2) ◁ Latch.C1 ⊞ '
            r'Latch.W1(α))))]₈₋₄ ◁ Perm(7, 0, 6, 3, 1, 2, 4, 5)')
        assert unicode(expr) == expected
        UnicodePrinter.update_registry(registry)
        expected = (
            r'Perm(1, 2, 3, 4, 5, 6, 7, 0) ◁ [(cid(4) ⊞ Perm(0, 4, 1, 2, 3) ◁ '
            r'(B11)) ◁ Perm(0, 1, 2, 3, 4, 6, 7, 8, 5) ◁ '
            r'(Perm(0, 1, 2, 3, 4, 7, 5, 6) ◁ (Perm(0, 1, 5, 3, 4, 2) ◁ '
            r'[(cid(2) ⊞ (B3) ◁ Perm(0, 2, 1) ◁ (B12)) ◁ '
            r'Perm(0, 1, 4, 5, 6, 2, 3) ◁ ((cid(1) ⊞ (cid(1) ⊞ '
            r'(Phase3 ⊞ Phase2) ◁ B22) ◁ Perm(0, 1, 3, 2) ◁ (C2 ⊞ W2)) ◁ '
            r'(B21 ◁ (Phase1)))]₄₋₀) ◁ (cid(4) ⊞ Perm(0, 2, 3, 1) ◁ '
            r'(Perm(1, 0, 2) ◁ C1 ⊞ W1)))]₈₋₄ ◁ Perm(7, 0, 6, 3, 1, 2, 4, 5)')
        assert unicode(expr) == expected
        UnicodePrinter.register(expr.operands[1], 'main_term')
        expected = (
            'Perm(1, 2, 3, 4, 5, 6, 7, 0) ◁ main_term '
            '◁ Perm(7, 0, 6, 3, 1, 2, 4, 5)')
        assert unicode(expr) == expected
    UnicodePrinter.clear_registry()
