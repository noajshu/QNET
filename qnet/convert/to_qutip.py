"""Conversion of QNET expressions to qutip objects."""
import re
import qutip
from sympy import symbols
from sympy.utilities.lambdify import lambdify
from scipy.sparse import csr_matrix
from numpy import (
        array as np_array,
        shape as np_shape,
        hstack as np_hstack,
        diag as np_diag,
        ones as np_ones,
        zeros as np_zeros,
        ndarray,
        arange,
        cos as np_cos,
        sin as np_sin,
        eye as np_eye,
        argwhere,
        complex128, float64)
from qnet.algebra.abstract_algebra import prod, AlgebraError
from qnet.algebra.operator_algebra import (
        IdentityOperator, ZeroOperator, LocalOperator, Create, Destroy, Jz,
        Jplus, Jminus, Phase, Displace, Squeeze, LocalSigma, OperatorOperation,
        OperatorPlus, OperatorTimes, ScalarTimesOperator, Adjoint,
        PseudoInverse, OperatorTrace, NullSpaceProjector, Operation, Operator)
from qnet.algebra.state_algebra import (
        Ket, BraKet, KetBra, BasisKet, CoherentStateKet, KetPlus, TensorKet,
        ScalarTimesKet, OperatorTimesKet)
from qnet.algebra.super_operator_algebra import (
        SuperOperator, IdentitySuperOperator, SuperOperatorPlus,
        SuperOperatorTimes, ScalarTimesSuperOperator, SPre, SPost,
        SuperOperatorTimesOperator, ZeroSuperOperator)


DENSE_DIMENSION_LIMIT = 1000


def convert_to_qutip(expr, full_space=None, mapping=None):
    """Convert a QNET expression to a qutip object

    Args:
        expr: a QNET expression
        full_space (qnet.algebra.hilbert_space_algebra.HilbertSpace): The
            Hilbert space in which `expr` is defined. If not given,
            ``expr.space`` is used. The Hilbert space must have a well-defined
            basis.
        mapping (dict): A mapping of any (sub-)expression to either a
            `quip.Qobj` directly, or to a callable that will convert the
            expression into a `qutip.Qobj`. Useful for e.g. supplying objects
            for symbols
    Raises:
        ValueError: if `expr` is not in `full_space`, or if `expr` cannot be
            converted.
    """
    if full_space is None:
        full_space = expr.space
    if not expr.space.is_tensor_factor_of(full_space):
        raise ValueError("expr must be in full_space")
    if mapping is not None:
        if expr in mapping:
            ret = mapping[expr]
            if isinstance(ret, qutip.Qobj):
                return ret
            else:
                assert callable(ret)
                return ret(expr)
    if expr is IdentityOperator:
        local_spaces = full_space.local_factors()
        if len(local_spaces) == 0:
            raise ValueError("full_space %s does not have local factors"
                             % full_space)
        else:
            return qutip.tensor(*[qutip.qeye(s.dimension)
                                  for s in local_spaces])
    elif expr is ZeroOperator:
        return qutip.tensor(
            *[qutip.Qobj(csr_matrix((s.dimension, s.dimension)))
              for s in full_space.local_factors()]
        )
    elif isinstance(expr, LocalOperator):
        return _convert_local_operator_to_qutip(expr, full_space, mapping)
    elif isinstance(expr, OperatorOperation):
        return _convert_operator_operation_to_qutip(expr, full_space, mapping)
    elif isinstance(expr, ScalarTimesOperator):
        return complex(expr.coeff) * \
                    convert_to_qutip(expr.term, full_space=full_space,
                                     mapping=mapping)
    elif isinstance(expr, OperatorTrace):
        raise NotImplementedError('Cannot convert OperatorTrace to '
                                  'qutip')
        # actually, this is perfectly doable in principle, but requires a bit
        # of work
    elif isinstance(expr, Ket):
        return _convert_ket_to_qutip(expr, full_space, mapping)
    elif isinstance(expr, SuperOperator):
        return _convert_superoperator_to_qutip(expr, full_space, mapping)
    elif isinstance(expr, Operation):
        # This is assumed to be an Operation on states, as we have handled all
        # other Operations above. Eventually, a StateOperation should be
        # defined as a common superclass for the Operations in the state
        # algebra
        return _convert_state_operation_to_qutip(expr, full_space, mapping)
    else:
        raise ValueError("Cannot convert '%s' of type %s"
                         % (str(expr), type(expr)))


def SLH_to_qutip(slh, full_space=None, time_symbol=None,
                 convert_as='pyfunc'):
    """
    Generate and return QuTiP representation matrices for the Hamiltonian
    and the collapse operators.

    Args:
        slh (SLH): The SLH object from which to generate the qutip data
        full_space (HilbertSpace or None): The Hilbert space in which to
            represent the operators. If None, the space of `shl` will be used
        time_symbol (sympy.Symbol or None): The symbol (if any) expressing time
            dependence (usually 't')
        convert_as (str): How to express time dependencies to qutip. Must be
            'pyfunc' or 'str'

    Returns:
        tuple ``(H, [L1, L2, ...])`` as numerical `qutip.Qobj` representations,
            where ``H`` and each ``L`` may be a nested list to express time
            dependence, e.g.  ``H = [H0, [H1, eps_t]]``, where ``H0`` and
            ``H1`` are of type `qutip.Qobj`, and ``eps_t`` is either a string
            (``convert_as='str'``) or a function (``convert_as='pyfunc'``)
    """
    if full_space:
        if not full_space >= slh.space:
            raise AlgebraError("full_space="+str(full_space)+" needs to "
                               "at least include slh.space = "+str(slh.space))
    else:
        full_space = slh.space
    if time_symbol is None:
        H = convert_to_qutip(slh.H, full_space)
        Ls = [convert_to_qutip(L, full_space) for L in slh.L.matrix.flatten()
              if isinstance(L, Operator)]
    else:
        H = _time_dependent_to_qutip(slh.H, full_space, time_symbol,
                                     convert_as)
        Ls = []
        for L in slh.L.matrix.flatten():
            Ls.append(_time_dependent_to_qutip(L, full_space, time_symbol,
                                               convert_as))
    return H, Ls


def _convert_local_operator_to_qutip(expr, full_space, mapping):
    """Convert a LocalOperator instance to qutip"""
    n = full_space.dimension
    if full_space != expr.space:
        all_spaces = full_space.local_factors()
        own_space_index = all_spaces.index(expr.space)
        return qutip.tensor(
            *([qutip.qeye(s.dimension)
               for s in all_spaces[:own_space_index]] +
              [convert_to_qutip(expr, expr.space, mapping=mapping), ] +
              [qutip.qeye(s.dimension)
               for s in all_spaces[own_space_index + 1:]])
        )
    if isinstance(expr, (Create, Jz, Jplus)):
        return qutip.create(n)
    elif isinstance(expr, (Destroy, Jminus)):
        return qutip.destroy(n)
    elif isinstance(expr, Phase):
        arg = complex(expr.operands[1]) * arange(n)
        d = np_cos(arg) + 1j * np_sin(arg)
        return qutip.Qobj(np_diag(d))
    elif isinstance(expr, Displace):
        alpha = expr.operands[1]
        return qutip.displace(n, alpha)
    elif isinstance(expr, Squeeze):
        eta = expr.operands[1]
        return qutip.displace(n, eta)
    elif isinstance(expr, LocalSigma):
        k, j = expr.operands[1:]
        ket = qutip.basis(n, expr.space.basis.index(k))
        bra = qutip.basis(n, expr.space.basis.index(j)).dag()
        return ket * bra
    else:
        raise ValueError("Cannot convert '%s' of type %s"
                         % (str(expr), type(expr)))


def _convert_operator_operation_to_qutip(expr, full_space, mapping):
    if isinstance(expr, OperatorPlus):
        return sum((convert_to_qutip(op, full_space, mapping=mapping)
                    for op in expr.operands), 0)
    elif isinstance(expr, OperatorTimes):
        # if any factor acts non-locally, we need to expand distributively.
        if any(len(op.space) > 1 for op in expr.operands):
            se = expr.expand()
            if se == expr:
                raise ValueError("Cannot represent as QuTiP object: {!s}"
                                 .format(expr))
            return convert_to_qutip(se, full_space, mapping=mapping)
        all_spaces = full_space.local_factors()
        by_space = []
        ck = 0
        for ls in all_spaces:
            # group factors by associated local space
            ls_ops = [convert_to_qutip(o, o.space, mapping=mapping)
                      for o in expr.operands if o.space == ls]
            if len(ls_ops):
                # compute factor associated with local space
                by_space.append(prod(ls_ops))
                ck += len(ls_ops)
            else:
                # if trivial action, take identity matrix
                by_space.append(qutip.qeye(ls.dimension))
        assert ck == len(expr.operands)
        # combine local factors in tensor product
        return qutip.tensor(*by_space)
    elif isinstance(expr, Adjoint):
        return convert_to_qutip(qutip.dag(expr.operands[0]), full_space,
                                mapping=mapping)
    elif isinstance(expr, PseudoInverse):
        mo = convert_to_qutip(expr.operand, full_space=full_space,
                              mapping=mapping)
        if full_space.dimension <= DENSE_DIMENSION_LIMIT:
            arr = mo.data.toarray()
            from scipy.linalg import pinv
            piarr = pinv(arr)
            pimo = qutip.Qobj(piarr)
            pimo.dims = mo.dims
            pimo.isherm = mo.isherm
            pimo.type = 'oper'
            return pimo
        raise NotImplementedError("Only implemented for smaller state "
                                  "spaces")
    elif isinstance(expr, NullSpaceProjector):
        mo = convert_to_qutip(expr.operand, full_space=full_space,
                              mapping=mapping)
        if full_space.dimension <= DENSE_DIMENSION_LIMIT:
            arr = mo.data.toarray()
            from scipy.linalg import svd
            # compute Singular Value Decomposition
            U, s, Vh = svd(arr)
            tol = 1e-8 * s[0]
            zero_svs = s < tol
            Vhzero = Vh[zero_svs, :]
            PKarr = Vhzero.conjugate().transpose().dot(Vhzero)
            PKmo = qutip.Qobj(PKarr)
            PKmo.dims = mo.dims
            PKmo.isherm = True
            PKmo.type = 'oper'
            return PKmo
        raise NotImplementedError("Only implemented for smaller state "
                                  "spaces")
    else:
        raise ValueError("Cannot convert '%s' of type %s"
                         % (str(expr), type(expr)))


def _convert_state_operation_to_qutip(expr, full_space, mapping):
    n = full_space.dimension
    if full_space != expr.space:
        all_spaces = full_space.local_factors()
        own_space_index = all_spaces.index(expr.space)
        return qutip.tensor(
            *([qutip.qeye(s.dimension)
               for s in all_spaces[:own_space_index]] +
              convert_to_qutip(expr, expr.space, mapping=mapping) +
              [qutip.qeye(s.dimension)
               for s in all_spaces[own_space_index + 1:]])
        )
    if isinstance(expr, BraKet):
        bq = convert_to_qutip(expr.bra, n, mapping=mapping)
        kq = convert_to_qutip(expr.ket, n, mapping=mapping)
        return bq * kq
    elif isinstance(expr, KetBra):
        bq = convert_to_qutip(expr.bra, n, mapping=mapping)
        kq = convert_to_qutip(expr.ket, n, mapping=mapping)
        return kq * bq
    else:
        raise ValueError("Cannot convert '%s' of type %s"
                         % (str(expr), type(expr)))


def _convert_ket_to_qutip(expr, full_space, mapping):
    n = full_space.dimension
    if full_space != expr.space:
        all_spaces = full_space.local_factors()
        own_space_index = all_spaces.index(expr.space)
        return qutip.tensor(
            *([qutip.qeye(s.dimension)
               for s in all_spaces[:own_space_index]] +
              convert_to_qutip(expr, expr.space, mapping=mapping) +
              [qutip.qeye(s.dimension)
               for s in all_spaces[own_space_index + 1:]])
        )
    if isinstance(expr, BasisKet):
        return qutip.basis(n, expr.space.basis.index(expr.operands[1]))
    elif isinstance(expr, CoherentStateKet):
        return qutip.coherent(n, complex(expr.operands[1]))
    elif isinstance(expr, KetPlus):
        return sum((convert_to_qutip(op, n, mapping=mapping)
                    for op in expr.operands), 0)
    elif isinstance(expr, TensorKet):
        if any(len(op.space) > 1 for op in expr.operands):
            se = expr.expand()
            if se == expr:
                raise ValueError("Cannot represent as QuTiP "
                                 "object: {!s}".format(expr))
            return convert_to_qutip(se, n, mapping=mapping)
        return qutip.tensor(*[convert_to_qutip(o, n, mapping=mapping)
                              for o in expr.operands])
    elif isinstance(expr, ScalarTimesKet):
        return complex(expr.coeff) * convert_to_qutip(expr.term, n,
                                                      mapping=mapping)
    elif isinstance(expr, OperatorTimesKet):
        return convert_to_qutip(expr.coeff, n, mapping=mapping) * \
                convert_to_qutip(expr.term, n, mapping=mapping)
    else:
        raise ValueError("Cannot convert '%s' of type %s"
                         % (str(expr), type(expr)))


def _convert_superoperator_to_qutip(expr, full_space, mapping):
    if full_space != expr.space:
        all_spaces = full_space.local_factors()
        own_space_index = all_spaces.index(expr.space)
        return qutip.tensor(
            *([qutip.qeye(s.dimension)
               for s in all_spaces[:own_space_index]] +
              convert_to_qutip(expr, expr.space, mapping=mapping) +
              [qutip.qeye(s.dimension)
               for s in all_spaces[own_space_index + 1:]])
        )
    if isinstance(expr, IdentitySuperOperator):
        return qutip.spre(qutip.tensor(*[qutip.qeye(s.dimension)
                                         for s in full_space.local_factors()]))
    elif isinstance(expr, SuperOperatorPlus):
        return sum((convert_to_qutip(op, full_space, mapping=mapping)
                    for op in expr.operands), 0)
    elif isinstance(expr, SuperOperatorTimes):
        ops_qutip = [convert_to_qutip(o, full_space, mapping=mapping)
                     for o in expr.operands]
        return prod(ops_qutip)
    elif isinstance(expr, ScalarTimesSuperOperator):
        return complex(expr.coeff) * \
                convert_to_qutip(expr.term, full_space, mapping=mapping)
    elif isinstance(expr, SPre):
        return qutip.spre(convert_to_qutip(
                                        expr.operands[0], full_space, mapping))
    elif isinstance(expr, SPost):
        return qutip.spost(convert_to_qutip(
                                        expr.operands[0], full_space, mapping))
    elif isinstance(expr, SuperOperatorTimesOperator):
        sop, op = expr.operands
        return (convert_to_qutip(sop, full_space, mapping=mapping) *
                convert_to_qutip(op, full_space, mapping=mapping))
    elif isinstance(expr, ZeroSuperOperator):
        return qutip.spre(convert_to_qutip(ZeroOperator, full_space,
                          mapping=mapping))
    else:
        raise ValueError("Cannot convert '%s' of type %s"
                         % (str(expr), type(expr)))


def _time_dependent_to_qutip(
        op, full_space=None, time_symbol=symbols("t", real=True),
        convert_as='pyfunc'):
    """Convert a possiblty time-dependent operator into the nested-list
    structure required by QuTiP"""
    if full_space is None:
        full_space = op.space
    if time_symbol in op.all_symbols():
        op = op.expand()
        if isinstance(op, OperatorPlus):
            result = []
            for o in op.operands:
                if time_symbol not in o.all_symbols():
                    if len(result) == 0:
                        result.append(convert_to_qutip(o,
                                                       full_space=full_space))
                    else:
                        result[0] += convert_to_qutip(o, full_space=full_space)
            for o in op.operands:
                if time_symbol in o.all_symbols():
                    result.append(_time_dependent_to_qutip(o, full_space,
                                  time_symbol, convert_as))
            return result
        elif isinstance(op, ScalarTimesOperator):
            if convert_as == 'pyfunc':
                func_no_args = lambdify(time_symbol, op.coeff)
                if {time_symbol, } == op.coeff.free_symbols:
                    def func(t, args):
                        # args are ignored for increased efficiency, since we
                        # know there are no free symbols except t
                        return func_no_args(t)
                else:
                    def func(t, args):
                        return func_no_args(t).subs(args)
                coeff = func
            elif convert_as == 'str':
                # a bit of a hack to replace imaginary unit
                # TODO: we can probably use one of the sympy code generation
                # routines, or lambdify with 'numexpr' to implement this in a
                # more robust way
                coeff = re.sub("I", "(1.0j)", str(op.coeff))
            else:
                raise ValueError(("Invalid value '%s' for `convert_as`, must "
                                  "be one of 'str', 'pyfunc'") % convert_as)
            return [convert_to_qutip(op.term, full_space), coeff]
        else:
            raise ValueError("op cannot be expressed in qutip. It must have "
                             "the structure op = sum_i f_i(t) * op_i")
    else:
        return convert_to_qutip(op, full_space=full_space)