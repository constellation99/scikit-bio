# ----------------------------------------------------------------------------
# Copyright (c) 2013--, scikit-bio development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------

from __future__ import absolute_import, division, print_function

import unittest
import functools
import itertools

import six
import numpy as np
import numpy.testing as npt

from skbio import Sequence, DNA, RNA, Protein, TabularMSA
from skbio.sequence._iupac_sequence import IUPACSequence
from skbio.util import OperationError, UniqueError
from skbio.util._decorator import classproperty, overrides
from skbio.util._testing import ReallyEqualMixin, MetadataMixinTests


class TabularMSASubclass(TabularMSA):
    """Used for testing purposes."""
    pass


class Unorderable(object):
    """For testing unorderable objects in Python 2 and 3."""
    def __lt__(self, other):
        raise TypeError()
    __cmp__ = __lt__


class TestTabularMSA(unittest.TestCase, ReallyEqualMixin, MetadataMixinTests):
    def setUp(self):
        self._metadata_constructor_ = functools.partial(TabularMSA, [])

    def test_from_dict_empty(self):
        self.assertEqual(TabularMSA.from_dict({}), TabularMSA([], keys=[]))

    def test_from_dict_single_sequence(self):
        self.assertEqual(TabularMSA.from_dict({'foo': DNA('ACGT')}),
                         TabularMSA([DNA('ACGT')], keys=['foo']))

    def test_from_dict_multiple_sequences(self):
        msa = TabularMSA.from_dict(
            {1: DNA('ACG'), 2: DNA('GGG'), 3: DNA('TAG')})
        # Sort because order is arbitrary.
        msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([DNA('ACG'), DNA('GGG'), DNA('TAG')], keys=[1, 2, 3]))

    def test_from_dict_invalid_input(self):
        # Basic test to make sure error-checking in the TabularMSA constructor
        # is being invoked.
        with six.assertRaisesRegex(
                self, ValueError, 'must match the number of positions'):
            TabularMSA.from_dict({'a': DNA('ACG'), 'b': DNA('ACGT')})

    def test_constructor_invalid_dtype(self):
        with six.assertRaisesRegex(self, TypeError,
                                   'sequence.*alphabet.*Sequence'):
            TabularMSA([Sequence('')])

        with six.assertRaisesRegex(self, TypeError, 'sequence.*alphabet.*int'):
            TabularMSA([42, DNA('')])

    def test_constructor_not_monomorphic(self):
        with six.assertRaisesRegex(self, TypeError,
                                   'must match the type.*RNA.*DNA'):
            TabularMSA([DNA(''), RNA('')])

        with six.assertRaisesRegex(self, TypeError,
                                   'must match the type.*float.*Protein'):
            TabularMSA([Protein(''), Protein(''), 42.0, Protein('')])

    def test_constructor_unequal_length(self):
        with six.assertRaisesRegex(
                self, ValueError,
                'must match the number of positions.*1 != 0'):
            TabularMSA([Protein(''), Protein('P')])

        with six.assertRaisesRegex(
                self, ValueError,
                'must match the number of positions.*1 != 3'):
            TabularMSA([Protein('PAW'), Protein('ABC'), Protein('A')])

    def test_constructor_non_iterable(self):
        with self.assertRaises(TypeError):
            TabularMSA(42)

    def test_constructor_non_unique_keys(self):
        with six.assertRaisesRegex(self, UniqueError, 'Duplicate keys:.*42'):
            TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=lambda x: 42)

        with six.assertRaisesRegex(self, UniqueError, "Duplicate keys:.*'a'"):
            TabularMSA([DNA('', metadata={'id': 'a'}),
                        DNA('', metadata={'id': 'b'}),
                        DNA('', metadata={'id': 'a'})],
                       minter='id')

        with six.assertRaisesRegex(self, UniqueError, 'Duplicate keys:.*42'):
            TabularMSA([DNA('ACGT'), DNA('TGCA')], keys=iter([42, 42]))

    def test_constructor_non_hashable_keys(self):
        with self.assertRaises(TypeError):
            TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=lambda x: [42])

        with self.assertRaises(TypeError):
            TabularMSA([DNA('ACGT'), DNA('TGCA')], keys=iter([[42], [42]]))

    def test_constructor_minter_and_keys_both_provided(self):
        with six.assertRaisesRegex(self, ValueError, 'both.*minter.*keys'):
            TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str, keys=['a', 'b'])

    def test_constructor_keys_length_mismatch(self):
        with six.assertRaisesRegex(self, ValueError,
                                   'Number.*keys.*number.*sequences: 0 != 2'):
            TabularMSA([DNA('ACGT'), DNA('TGCA')], keys=iter([]))

    def test_constructor_empty_no_keys(self):
        # sequence empty
        msa = TabularMSA([])
        self.assertIsNone(msa.dtype)
        self.assertEqual(msa.shape, (0, 0))
        with self.assertRaises(OperationError):
            msa.keys
        with self.assertRaises(StopIteration):
            next(iter(msa))

        # position empty
        seqs = [DNA(''), DNA('')]
        msa = TabularMSA(seqs)
        self.assertIs(msa.dtype, DNA)
        self.assertEqual(msa.shape, (2, 0))
        with self.assertRaises(OperationError):
            msa.keys
        self.assertEqual(list(msa), seqs)

    def test_constructor_empty_with_keys(self):
        # sequence empty
        msa = TabularMSA([], minter=lambda x: x)
        npt.assert_array_equal(msa.keys, np.array([]))

        msa = TabularMSA([], keys=iter([]))
        npt.assert_array_equal(msa.keys, np.array([]))

        # position empty
        msa = TabularMSA([DNA('', metadata={'id': 42}),
                          DNA('', metadata={'id': 43})], minter='id')
        npt.assert_array_equal(msa.keys, np.array([42, 43]))

        msa = TabularMSA([DNA(''), DNA('')], keys=iter([42, 43]))
        npt.assert_array_equal(msa.keys, np.array([42, 43]))

    def test_constructor_non_empty_no_keys(self):
        # 1x3
        seqs = [DNA('ACG')]
        msa = TabularMSA(seqs)
        self.assertIs(msa.dtype, DNA)
        self.assertEqual(msa.shape, (1, 3))
        with self.assertRaises(OperationError):
            msa.keys
        self.assertEqual(list(msa), seqs)

        # 3x1
        seqs = [DNA('A'), DNA('C'), DNA('G')]
        msa = TabularMSA(seqs)
        self.assertIs(msa.dtype, DNA)
        self.assertEqual(msa.shape, (3, 1))
        with self.assertRaises(OperationError):
            msa.keys
        self.assertEqual(list(msa), seqs)

    def test_constructor_non_empty_with_keys(self):
        seqs = [DNA('ACG'), DNA('CGA'), DNA('GTT')]
        msa = TabularMSA(seqs, minter=str)
        self.assertIs(msa.dtype, DNA)
        self.assertEqual(msa.shape, (3, 3))
        npt.assert_array_equal(msa.keys, np.array(['ACG', 'CGA', 'GTT']))
        self.assertEqual(list(msa), seqs)

        msa = TabularMSA(seqs, keys=iter([42, 43, 44]))
        npt.assert_array_equal(msa.keys, np.array([42, 43, 44]))

    def test_constructor_works_with_iterator(self):
        seqs = [DNA('ACG'), DNA('CGA'), DNA('GTT')]
        msa = TabularMSA(iter(seqs), minter=str)
        self.assertIs(msa.dtype, DNA)
        self.assertEqual(msa.shape, (3, 3))
        npt.assert_array_equal(msa.keys, np.array(['ACG', 'CGA', 'GTT']))
        self.assertEqual(list(msa), seqs)

    def test_dtype(self):
        self.assertIsNone(TabularMSA([]).dtype)
        self.assertIs(TabularMSA([Protein('')]).dtype, Protein)

        with self.assertRaises(AttributeError):
            TabularMSA([]).dtype = DNA

        with self.assertRaises(AttributeError):
            del TabularMSA([]).dtype

    def test_shape(self):
        shape = TabularMSA([DNA('ACG'), DNA('GCA')]).shape
        self.assertEqual(shape, (2, 3))
        self.assertEqual(shape.sequence, shape[0])
        self.assertEqual(shape.position, shape[1])
        with self.assertRaises(TypeError):
            shape[0] = 3

        with self.assertRaises(AttributeError):
            TabularMSA([]).shape = (3, 3)

        with self.assertRaises(AttributeError):
            del TabularMSA([]).shape

    def test_keys_getter(self):
        with six.assertRaisesRegex(self, OperationError,
                                   'Keys do not exist.*reindex'):
            TabularMSA([]).keys

        keys = TabularMSA([DNA('AC'), DNA('AG'), DNA('AT')], minter=str).keys
        self.assertIsInstance(keys, np.ndarray)
        self.assertEqual(keys.dtype, object)
        npt.assert_array_equal(keys, np.array(['AC', 'AG', 'AT']))

        # immutable
        with self.assertRaises(ValueError):
            keys[1] = 'AA'
        # original state is maintained
        npt.assert_array_equal(keys, np.array(['AC', 'AG', 'AT']))

    def test_keys_mixed_type(self):
        msa = TabularMSA([DNA('AC'), DNA('CA'), DNA('AA')],
                         keys=['abc', 'd', 42])
        npt.assert_array_equal(msa.keys,
                               np.array(['abc', 'd', 42], dtype=object))

    def test_keys_update_subset_of_keys(self):
        # keys can be copied, modified, then re-set
        msa = TabularMSA([DNA('AC'), DNA('AG'), DNA('AT')], minter=str)
        npt.assert_array_equal(msa.keys, np.array(['AC', 'AG', 'AT']))

        new_keys = msa.keys.copy()
        new_keys[1] = 42
        msa.keys = new_keys
        npt.assert_array_equal(msa.keys,
                               np.array(['AC', 42, 'AT'], dtype=object))

        self.assertFalse(msa.keys.flags.writeable)
        self.assertTrue(new_keys.flags.writeable)
        new_keys[1] = 'GG'
        npt.assert_array_equal(msa.keys,
                               np.array(['AC', 42, 'AT'], dtype=object))

    def test_keys_setter_empty(self):
        msa = TabularMSA([])
        self.assertFalse(msa.has_keys())
        msa.keys = iter([])
        npt.assert_array_equal(msa.keys, np.array([]))

    def test_keys_setter_non_empty(self):
        msa = TabularMSA([DNA('AC'), DNA('AG'), DNA('AT')])
        self.assertFalse(msa.has_keys())
        msa.keys = range(3)
        npt.assert_array_equal(msa.keys, np.array([0, 1, 2]))
        msa.keys = range(3, 6)
        npt.assert_array_equal(msa.keys, np.array([3, 4, 5]))

    def test_keys_setter_length_mismatch(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with six.assertRaisesRegex(self, ValueError,
                                   'Number.*keys.*number.*sequences: 3 != 2'):
            msa.keys = iter(['ab', 'cd', 'ef'])

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

    def test_keys_setter_non_unique_keys(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with six.assertRaisesRegex(self, UniqueError, 'Duplicate keys:.*42'):
            msa.keys = [42, 42]

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

    def test_keys_setter_non_hashable_keys(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with self.assertRaises(TypeError):
            msa.keys = [[42], [42]]

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

    def test_keys_deleter_no_keys(self):
        msa = TabularMSA([])
        self.assertFalse(msa.has_keys())
        del msa.keys
        self.assertFalse(msa.has_keys())

    def test_keys_deleter_with_keys(self):
        msa = TabularMSA([RNA('UUU'), RNA('AAA')], minter=str)
        self.assertTrue(msa.has_keys())
        del msa.keys
        self.assertFalse(msa.has_keys())

    def test_bool(self):
        self.assertFalse(TabularMSA([]))
        self.assertFalse(TabularMSA([RNA('')]))
        self.assertFalse(
            TabularMSA([RNA('', metadata={'id': 1}),
                        RNA('', metadata={'id': 2})], minter='id'))

        self.assertTrue(TabularMSA([RNA('U')]))
        self.assertTrue(TabularMSA([RNA('--'), RNA('..')]))
        self.assertTrue(TabularMSA([RNA('AUC'), RNA('GCA')]))

    def test_len(self):
        self.assertEqual(len(TabularMSA([])), 0)
        self.assertEqual(len(TabularMSA([DNA('')])), 1)
        self.assertEqual(len(TabularMSA([DNA('AT'), DNA('AG'), DNA('AT')])), 3)

    def test_iter(self):
        with self.assertRaises(StopIteration):
            next(iter(TabularMSA([])))

        seqs = [DNA(''), DNA('')]
        self.assertEqual(list(iter(TabularMSA(seqs))), seqs)

        seqs = [DNA('AAA'), DNA('GCT')]
        self.assertEqual(list(iter(TabularMSA(seqs))), seqs)

    def test_reversed(self):
        with self.assertRaises(StopIteration):
            next(reversed(TabularMSA([])))

        seqs = [DNA(''), DNA('', metadata={'id': 42})]
        self.assertEqual(list(reversed(TabularMSA(seqs))), seqs[::-1])

        seqs = [DNA('AAA'), DNA('GCT')]
        self.assertEqual(list(reversed(TabularMSA(seqs))), seqs[::-1])

    def test_eq_and_ne(self):
        # Each element contains the components necessary to construct a
        # TabularMSA object: seqs and kwargs. None of these objects (once
        # constructed) should compare equal to one another.
        components = [
            # empties
            ([], {}),
            ([], {'minter': str}),
            ([RNA('')], {}),
            ([RNA('')], {'minter': str}),

            # 1x1
            ([RNA('U')], {'minter': str}),

            # 2x3
            ([RNA('AUG'), RNA('GUA')], {'minter': str}),

            ([RNA('AG'), RNA('GG')], {}),
            # has keys
            ([RNA('AG'), RNA('GG')], {'minter': str}),
            # different dtype
            ([DNA('AG'), DNA('GG')], {'minter': str}),
            # different keys
            ([RNA('AG'), RNA('GG')], {'minter': lambda x: str(x) + '42'}),
            # different sequence metadata
            ([RNA('AG', metadata={'id': 42}), RNA('GG')], {'minter': str}),
            # different sequence data, same keys
            ([RNA('AG'), RNA('GA')],
             {'minter': lambda x: 'AG' if 'AG' in x else 'GG'}),
            # different MSA metadata
            ([RNA('AG'), RNA('GG')], {'metadata': {'foo': 42}}),
            ([RNA('AG'), RNA('GG')], {'metadata': {'foo': 43}}),
            ([RNA('AG'), RNA('GG')], {'metadata': {'foo': 42, 'bar': 43}}),
        ]

        for seqs, kwargs in components:
            obj = TabularMSA(seqs, **kwargs)
            self.assertReallyEqual(obj, obj)
            self.assertReallyEqual(obj, TabularMSA(seqs, **kwargs))
            self.assertReallyEqual(obj, TabularMSASubclass(seqs, **kwargs))

        for (seqs1, kwargs1), (seqs2, kwargs2) in \
                itertools.combinations(components, 2):
            obj1 = TabularMSA(seqs1, **kwargs1)
            obj2 = TabularMSA(seqs2, **kwargs2)
            self.assertReallyNotEqual(obj1, obj2)
            self.assertReallyNotEqual(obj1,
                                      TabularMSASubclass(seqs2, **kwargs2))

        # completely different types
        msa = TabularMSA([])
        self.assertReallyNotEqual(msa, 42)
        self.assertReallyNotEqual(msa, [])
        self.assertReallyNotEqual(msa, {})
        self.assertReallyNotEqual(msa, '')

    def test_eq_constructed_from_different_iterables_compare_equal(self):
        msa1 = TabularMSA([DNA('ACGT')])
        msa2 = TabularMSA((DNA('ACGT'),))
        self.assertReallyEqual(msa1, msa2)

    def test_eq_missing_metadata(self):
        self.assertReallyEqual(TabularMSA([DNA('A')]),
                               TabularMSA([DNA('A')], metadata={}))

    def test_eq_handles_missing_metadata_efficiently(self):
        msa1 = TabularMSA([DNA('ACGT')])
        msa2 = TabularMSA([DNA('ACGT')])
        self.assertReallyEqual(msa1, msa2)

        self.assertIsNone(msa1._metadata)
        self.assertIsNone(msa2._metadata)

    def test_eq_ignores_minter_str_and_lambda(self):
        # as long as the keys generated by the minters are the same, it
        # doesn't matter whether the minters are equal.
        msa1 = TabularMSA([DNA('ACGT', metadata={'id': 'a'})], minter='id')
        msa2 = TabularMSA([DNA('ACGT', metadata={'id': 'a'})],
                          minter=lambda x: x.metadata['id'])
        self.assertReallyEqual(msa1, msa2)

    def test_eq_minter_and_keys(self):
        # as long as the keys generated by the minters are the same, it
        # doesn't matter whether the minters are equal.
        msa1 = TabularMSA([DNA('ACGT', metadata={'id': 'a'})], keys=['a'])
        msa2 = TabularMSA([DNA('ACGT', metadata={'id': 'a'})], minter='id')
        self.assertReallyEqual(msa1, msa2)

    def test_has_metadata(self):
        msa = TabularMSA([])
        self.assertFalse(msa.has_metadata())
        # Handles metadata efficiently.
        self.assertIsNone(msa._metadata)

        self.assertFalse(TabularMSA([], metadata={}).has_metadata())

        self.assertTrue(TabularMSA([], metadata={'': ''}).has_metadata())
        self.assertTrue(TabularMSA([], metadata={'foo': 42}).has_metadata())

    def test_has_keys(self):
        self.assertFalse(TabularMSA([]).has_keys())
        self.assertTrue(TabularMSA([], minter=str).has_keys())

        self.assertFalse(TabularMSA([DNA('')]).has_keys())
        self.assertTrue(TabularMSA([DNA('')], minter=str).has_keys())

        self.assertFalse(TabularMSA([DNA('ACG'), DNA('GCA')]).has_keys())
        self.assertTrue(
            TabularMSA([DNA('ACG', metadata={'id': 1}),
                        DNA('GCA', metadata={'id': 2})],
                       minter='id').has_keys())

        msa = TabularMSA([])
        self.assertFalse(msa.has_keys())
        msa.reindex(minter=str)
        self.assertTrue(msa.has_keys())
        msa.reindex()
        self.assertFalse(msa.has_keys())

    def test_reindex_empty(self):
        # sequence empty
        msa = TabularMSA([])
        msa.reindex()
        self.assertEqual(msa, TabularMSA([]))
        self.assertFalse(msa.has_keys())

        msa.reindex(minter=str)
        self.assertEqual(msa, TabularMSA([], minter=str))
        npt.assert_array_equal(msa.keys, np.array([]))

        msa.reindex(keys=iter([]))
        self.assertEqual(msa, TabularMSA([], keys=iter([])))
        npt.assert_array_equal(msa.keys, np.array([]))

        # position empty
        msa = TabularMSA([DNA('')])
        msa.reindex()
        self.assertEqual(msa, TabularMSA([DNA('')]))
        self.assertFalse(msa.has_keys())

        msa.reindex(minter=str)
        self.assertEqual(msa, TabularMSA([DNA('')], minter=str))
        npt.assert_array_equal(msa.keys, np.array(['']))

        msa.reindex(keys=iter(['a']))
        self.assertEqual(msa, TabularMSA([DNA('')], keys=iter(['a'])))
        npt.assert_array_equal(msa.keys, np.array(['a']))

    def test_reindex_non_empty(self):
        msa = TabularMSA([DNA('ACG', metadata={'id': 1}),
                          DNA('AAA', metadata={'id': 2})], minter=str)
        npt.assert_array_equal(msa.keys, np.array(['ACG', 'AAA']))

        msa.reindex(minter='id')
        self.assertEqual(
            msa,
            TabularMSA([DNA('ACG', metadata={'id': 1}),
                        DNA('AAA', metadata={'id': 2})], minter='id'))
        npt.assert_array_equal(msa.keys, np.array([1, 2]))

        msa.reindex(keys=iter('ab'))
        self.assertEqual(
            msa,
            TabularMSA([DNA('ACG', metadata={'id': 1}),
                        DNA('AAA', metadata={'id': 2})], keys=iter('ab')))
        npt.assert_array_equal(msa.keys, np.array(['a', 'b']))

        msa.reindex()
        self.assertFalse(msa.has_keys())

    def test_reindex_makes_copy_of_keys(self):
        msa = TabularMSA([DNA('AC'), DNA('AG'), DNA('AT')])
        keys = np.asarray([1, 2, 3])
        msa.reindex(keys=keys)
        npt.assert_array_equal(msa.keys, np.array([1, 2, 3]))

        self.assertFalse(msa.keys.flags.writeable)
        self.assertTrue(keys.flags.writeable)
        keys[1] = 42
        npt.assert_array_equal(msa.keys, np.array([1, 2, 3]))

    def test_reindex_minter_and_keys_both_provided(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with six.assertRaisesRegex(self, ValueError, 'both.*minter.*keys'):
            msa.reindex(minter=str, keys=['a', 'b'])

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

    def test_reindex_keys_length_mismatch(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with six.assertRaisesRegex(self, ValueError,
                                   'Number.*keys.*number.*sequences: 0 != 2'):
            msa.reindex(keys=iter([]))

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

    def test_reindex_non_unique_keys(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with six.assertRaisesRegex(self, UniqueError, 'Duplicate keys:.*42'):
            msa.reindex(minter=lambda x: 42)

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

        with six.assertRaisesRegex(self, UniqueError, 'Duplicate keys:.*42'):
            msa.reindex(keys=[42, 42])

        npt.assert_array_equal(msa.keys, keys)

    def test_reindex_non_hashable_keys(self):
        msa = TabularMSA([DNA('ACGT'), DNA('TGCA')], minter=str)
        keys = np.array(['ACGT', 'TGCA'])
        npt.assert_array_equal(msa.keys, keys)

        with self.assertRaises(TypeError):
            msa.reindex(minter=lambda x: [42])

        # original state is maintained
        npt.assert_array_equal(msa.keys, keys)

        with self.assertRaises(TypeError):
            msa.reindex(keys=[[42], [42]])

        npt.assert_array_equal(msa.keys, keys)

    def test_sort_no_msa_keys_and_key_not_specified(self):
        msa = TabularMSA([])
        with self.assertRaises(OperationError):
            msa.sort()
        # original state is maintained
        self.assertEqual(msa, TabularMSA([]))

        msa = TabularMSA([DNA('TC'), DNA('AA')])
        with self.assertRaises(OperationError):
            msa.sort()
        self.assertEqual(msa, TabularMSA([DNA('TC'), DNA('AA')]))

    def test_sort_on_unorderable_msa_keys(self):
        unorderable = Unorderable()
        msa = TabularMSA([DNA('AAA'), DNA('ACG')], keys=[42, unorderable])
        with self.assertRaises(TypeError):
            msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([DNA('AAA'), DNA('ACG')], keys=[42, unorderable]))

    def test_sort_on_unorderable_key(self):
        unorderable = Unorderable()
        msa = TabularMSA([
            DNA('AAA', metadata={'id': 42}),
            DNA('ACG', metadata={'id': unorderable})], keys=[42, 43])
        with self.assertRaises(TypeError):
            msa.sort(key='id')
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('AAA', metadata={'id': 42}),
                DNA('ACG', metadata={'id': unorderable})], keys=[42, 43]))

    def test_sort_on_invalid_key(self):
        msa = TabularMSA([DNA('AAA'), DNA('ACG')], keys=[42, 43])
        with self.assertRaises(KeyError):
            msa.sort(key='id')
        self.assertEqual(
            msa,
            TabularMSA([DNA('AAA'), DNA('ACG')], keys=[42, 43]))

    def test_sort_empty_on_msa_keys(self):
        msa = TabularMSA([], keys=[])
        msa.sort()
        self.assertEqual(msa, TabularMSA([], keys=[]))

        msa = TabularMSA([], keys=[])
        msa.sort(reverse=True)
        self.assertEqual(msa, TabularMSA([], keys=[]))

    def test_sort_single_sequence_on_msa_keys(self):
        msa = TabularMSA([DNA('ACGT')], keys=[42])
        msa.sort()
        self.assertEqual(msa, TabularMSA([DNA('ACGT')], keys=[42]))

        msa = TabularMSA([DNA('ACGT')], keys=[42])
        msa.sort(reverse=True)
        self.assertEqual(msa, TabularMSA([DNA('ACGT')], keys=[42]))

    def test_sort_multiple_sequences_on_msa_keys(self):
        msa = TabularMSA([
            DNA('TC'), DNA('GG'), DNA('CC')], keys=['z', 'a', 'b'])
        msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('GG'), DNA('CC'), DNA('TC')], keys=['a', 'b', 'z']))

        msa = TabularMSA([
            DNA('TC'), DNA('GG'), DNA('CC')], keys=['z', 'a', 'b'])
        msa.sort(reverse=True)
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('TC'), DNA('CC'), DNA('GG')], keys=['z', 'b', 'a']))

    def test_sort_empty_no_msa_keys_on_metadata_key(self):
        msa = TabularMSA([])
        msa.sort(key='id')
        self.assertEqual(msa, TabularMSA([]))

        msa = TabularMSA([])
        msa.sort(key='id', reverse=True)
        self.assertEqual(msa, TabularMSA([]))

    def test_sort_empty_no_msa_keys_on_callable_key(self):
        msa = TabularMSA([])
        msa.sort(key=str)
        self.assertEqual(msa, TabularMSA([]))

        msa = TabularMSA([])
        msa.sort(key=str, reverse=True)
        self.assertEqual(msa, TabularMSA([]))

    def test_sort_empty_with_msa_keys_on_metadata_key(self):
        msa = TabularMSA([], keys=[])
        msa.sort(key='id')
        self.assertEqual(msa, TabularMSA([], keys=[]))

        msa = TabularMSA([], keys=[])
        msa.sort(key='id', reverse=True)
        self.assertEqual(msa, TabularMSA([], keys=[]))

    def test_sort_empty_with_msa_keys_on_callable_key(self):
        msa = TabularMSA([], keys=[])
        msa.sort(key=str)
        self.assertEqual(msa, TabularMSA([], keys=[]))

        msa = TabularMSA([], keys=[])
        msa.sort(key=str, reverse=True)
        self.assertEqual(msa, TabularMSA([], keys=[]))

    def test_sort_single_sequence_no_msa_keys_on_metadata_key(self):
        msa = TabularMSA([RNA('UCA', metadata={'id': 42})])
        msa.sort(key='id')
        self.assertEqual(msa, TabularMSA([RNA('UCA', metadata={'id': 42})]))

        msa = TabularMSA([RNA('UCA', metadata={'id': 42})])
        msa.sort(key='id', reverse=True)
        self.assertEqual(msa, TabularMSA([RNA('UCA', metadata={'id': 42})]))

    def test_sort_single_sequence_no_msa_keys_on_callable_key(self):
        msa = TabularMSA([RNA('UCA')])
        msa.sort(key=str)
        self.assertEqual(msa, TabularMSA([RNA('UCA')]))

        msa = TabularMSA([RNA('UCA')])
        msa.sort(key=str, reverse=True)
        self.assertEqual(msa, TabularMSA([RNA('UCA')]))

    def test_sort_single_sequence_with_msa_keys_on_metadata_key(self):
        msa = TabularMSA([RNA('UCA', metadata={'id': 42})], keys=['foo'])
        msa.sort(key='id')
        self.assertEqual(
            msa, TabularMSA([RNA('UCA', metadata={'id': 42})], keys=['foo']))

        msa = TabularMSA([RNA('UCA', metadata={'id': 42})], keys=['foo'])
        msa.sort(key='id', reverse=True)
        self.assertEqual(
            msa, TabularMSA([RNA('UCA', metadata={'id': 42})], keys=['foo']))

    def test_sort_single_sequence_with_msa_keys_on_callable_key(self):
        msa = TabularMSA([RNA('UCA')], keys=['foo'])
        msa.sort(key=str)
        self.assertEqual(msa, TabularMSA([RNA('UCA')], keys=['foo']))

        msa = TabularMSA([RNA('UCA')], keys=['foo'])
        msa.sort(key=str, reverse=True)
        self.assertEqual(msa, TabularMSA([RNA('UCA')], keys=['foo']))

    def test_sort_multiple_sequences_no_msa_keys_on_metadata_key(self):
        msa = TabularMSA([RNA('UCA', metadata={'id': 41}),
                          RNA('AAA', metadata={'id': 44}),
                          RNA('GAC', metadata={'id': -1}),
                          RNA('GAC', metadata={'id': 42})])
        msa.sort(key='id')
        self.assertEqual(msa, TabularMSA([RNA('GAC', metadata={'id': -1}),
                                          RNA('UCA', metadata={'id': 41}),
                                          RNA('GAC', metadata={'id': 42}),
                                          RNA('AAA', metadata={'id': 44})]))

        msa = TabularMSA([RNA('UCA', metadata={'id': 41}),
                          RNA('AAA', metadata={'id': 44}),
                          RNA('GAC', metadata={'id': -1}),
                          RNA('GAC', metadata={'id': 42})])
        msa.sort(key='id', reverse=True)
        self.assertEqual(msa, TabularMSA([RNA('AAA', metadata={'id': 44}),
                                          RNA('GAC', metadata={'id': 42}),
                                          RNA('UCA', metadata={'id': 41}),
                                          RNA('GAC', metadata={'id': -1})]))

    def test_sort_multiple_sequences_no_msa_keys_on_callable_key(self):
        msa = TabularMSA([RNA('UCC'),
                          RNA('UCG'),
                          RNA('UCA')])
        msa.sort(key=str)
        self.assertEqual(msa, TabularMSA([RNA('UCA'), RNA('UCC'), RNA('UCG')]))

        msa = TabularMSA([RNA('UCC'),
                          RNA('UCG'),
                          RNA('UCA')])
        msa.sort(key=str, reverse=True)
        self.assertEqual(msa, TabularMSA([RNA('UCG'), RNA('UCC'), RNA('UCA')]))

    def test_sort_multiple_sequences_with_msa_keys_on_metadata_key(self):
        msa = TabularMSA([DNA('TCA', metadata={'#': 41.2}),
                          DNA('AAA', metadata={'#': 44.5}),
                          DNA('GAC', metadata={'#': 42.999})],
                         keys=[None, ('hello', 'world'), True])
        msa.sort(key='#')
        self.assertEqual(
            msa,
            TabularMSA([DNA('TCA', metadata={'#': 41.2}),
                        DNA('GAC', metadata={'#': 42.999}),
                        DNA('AAA', metadata={'#': 44.5})],
                       keys=[None, True, ('hello', 'world')]))

        msa = TabularMSA([DNA('TCA', metadata={'#': 41.2}),
                          DNA('AAA', metadata={'#': 44.5}),
                          DNA('GAC', metadata={'#': 42.999})],
                         keys=[None, ('hello', 'world'), True])
        msa.sort(key='#', reverse=True)
        self.assertEqual(
            msa,
            TabularMSA([DNA('AAA', metadata={'#': 44.5}),
                        DNA('GAC', metadata={'#': 42.999}),
                        DNA('TCA', metadata={'#': 41.2})],
                       keys=[('hello', 'world'), True, None]))

    def test_sort_multiple_sequences_with_msa_keys_on_callable_key(self):
        msa = TabularMSA([RNA('UCC'),
                          RNA('UCG'),
                          RNA('UCA')], keys=[1, 'abc', None])
        msa.sort(key=str)
        self.assertEqual(msa, TabularMSA([RNA('UCA'), RNA('UCC'), RNA('UCG')],
                                         keys=[None, 1, 'abc']))

        msa = TabularMSA([RNA('UCC'),
                          RNA('UCG'),
                          RNA('UCA')], keys=[1, 'abc', None])
        msa.sort(key=str, reverse=True)
        self.assertEqual(msa, TabularMSA([RNA('UCG'), RNA('UCC'), RNA('UCA')],
                                         keys=['abc', 1, None]))

    def test_sort_on_key_with_some_repeats(self):
        msa = TabularMSA([
            DNA('TCCG', metadata={'id': 10}),
            DNA('TAGG', metadata={'id': 10}),
            DNA('GGGG', metadata={'id': 8}),
            DNA('ACGT', metadata={'id': 0}),
            DNA('TAGG', metadata={'id': 10})], keys=range(5))
        msa.sort(key='id')
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('ACGT', metadata={'id': 0}),
                DNA('GGGG', metadata={'id': 8}),
                DNA('TCCG', metadata={'id': 10}),
                DNA('TAGG', metadata={'id': 10}),
                DNA('TAGG', metadata={'id': 10})], keys=[3, 2, 0, 1, 4]))

    def test_sort_on_key_with_all_repeats(self):
        msa = TabularMSA([
            DNA('TTT', metadata={'id': 'a'}),
            DNA('TTT', metadata={'id': 'b'}),
            DNA('TTT', metadata={'id': 'c'})], keys=range(3))
        msa.sort(key=str)
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('TTT', metadata={'id': 'a'}),
                DNA('TTT', metadata={'id': 'b'}),
                DNA('TTT', metadata={'id': 'c'})], keys=range(3)))

    def test_sort_mixed_key_types(self):
        msa = TabularMSA([
            DNA('GCG', metadata={'id': 41}),
            DNA('CGC', metadata={'id': 42.2}),
            DNA('TCT', metadata={'id': 42})])
        msa.sort(key='id')
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('GCG', metadata={'id': 41}),
                DNA('TCT', metadata={'id': 42}),
                DNA('CGC', metadata={'id': 42.2})]))

        msa = TabularMSA([
            DNA('GCG'),
            DNA('CGC'),
            DNA('TCT')], keys=[41, 42.2, 42])
        msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([
                DNA('GCG'),
                DNA('TCT'),
                DNA('CGC')], keys=[41, 42, 42.2]))

    def test_sort_already_sorted(self):
        msa = TabularMSA([DNA('TC'), DNA('GG'), DNA('CC')], keys=[1, 2, 3])
        msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([DNA('TC'), DNA('GG'), DNA('CC')], keys=[1, 2, 3]))

        msa = TabularMSA([DNA('TC'), DNA('GG'), DNA('CC')], keys=[3, 2, 1])
        msa.sort(reverse=True)
        self.assertEqual(
            msa,
            TabularMSA([DNA('TC'), DNA('GG'), DNA('CC')], keys=[3, 2, 1]))

    def test_sort_reverse_sorted(self):
        msa = TabularMSA([DNA('T'), DNA('G'), DNA('A')], keys=[3, 2, 1])
        msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([DNA('A'), DNA('G'), DNA('T')], keys=[1, 2, 3]))

        msa = TabularMSA([DNA('T'), DNA('G'), DNA('A')], keys=[1, 2, 3])
        msa.sort(reverse=True)
        self.assertEqual(
            msa,
            TabularMSA([DNA('A'), DNA('G'), DNA('T')], keys=[3, 2, 1]))

    def test_sort_identical_sequences(self):
        msa = TabularMSA([DNA(''), DNA(''), DNA('')], keys=['ab', 'aa', 'ac'])
        msa.sort()
        self.assertEqual(
            msa,
            TabularMSA([DNA(''), DNA(''), DNA('')], keys=['aa', 'ab', 'ac']))

    def test_to_dict_no_keys(self):
        with self.assertRaises(OperationError):
            TabularMSA([]).to_dict()

        with self.assertRaises(OperationError):
            TabularMSA([DNA('AGCT'), DNA('TCGA')]).to_dict()

    def test_to_dict_empty(self):
        self.assertEqual(TabularMSA([], keys=[]).to_dict(), {})
        self.assertEqual(TabularMSA([RNA('')], keys=['foo']).to_dict(),
                         {'foo': RNA('')})

    def test_to_dict_non_empty(self):
        seqs = [Protein('PAW', metadata={'id': 42}),
                Protein('WAP', metadata={'id': -999})]
        msa = TabularMSA(seqs, minter='id')
        self.assertEqual(msa.to_dict(), {42: seqs[0], -999: seqs[1]})

    def test_from_dict_to_dict_roundtrip(self):
        d = {}
        self.assertEqual(TabularMSA.from_dict(d).to_dict(), d)

        # can roundtrip even with mixed key types
        d1 = {'a': DNA('CAT'), 42: DNA('TAG')}
        d2 = TabularMSA.from_dict(d1).to_dict()
        self.assertEqual(d2, d1)
        self.assertIs(d1['a'], d2['a'])
        self.assertIs(d1[42], d2[42])


class TestAppend(unittest.TestCase):
    def setUp(self):
        self.msa = TabularMSA([DNA('ACGT'), DNA('TGCA')])
        self.msa_unmodified = TabularMSA([DNA('ACGT'), DNA('TGCA')])
        self.append_seq = DNA('GGGG')

        self.msa_with_keys = TabularMSA([DNA(''), DNA('')], keys=['a', 'b'])
        self.msa_with_keys_unmodified = TabularMSA([DNA(''), DNA('')],
                                                   keys=['a', 'b'])
        self.append_seq_with_keys = DNA('')
        self.append_key = 'c'
        self.msa_with_keys_after_append = \
            TabularMSA([DNA(''), DNA(''), self.append_seq_with_keys],
                       keys=['a', 'b', self.append_key])

    def test_to_empty_msa(self):
        expected = TabularMSA([DNA('ACGT')])
        msa = TabularMSA([])
        msa.append(DNA('ACGT'))
        self.assertEqual(msa, expected)

    def test_to_empty_msa_invalid_dtype(self):
        msa = TabularMSA([])
        with six.assertRaisesRegex(self, TypeError,
                                   'sequence.*alphabet.*Sequence'):
            msa.append(Sequence(''))
        self.assertEqual(msa, TabularMSA([]))

    def test_to_empty_msa_with_key(self):
        msa = TabularMSA([], keys=[])
        msa.append(DNA('ACGT', metadata={'id': 'a'}), key='a')
        self.assertEqual(msa, TabularMSA([DNA('ACGT', metadata={'id': 'a'})],
                                         keys=['a']))

    def test_to_empty_invalid_key_does_not_mutate_msa(self):
        msa = TabularMSA([], keys=[])
        with self.assertRaises(TypeError):
            unhashable_key = {}
            msa.append(DNA('ACGT'), key=unhashable_key)
        self.assertEqual(msa, TabularMSA([], keys=[]))

    def test_wrong_dtype_rna(self):
        with six.assertRaisesRegex(self, TypeError,
                                   'must match the type.*RNA.*DNA'):
            self.msa.append(RNA('UUUU'))
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_wrong_dtype_float(self):
        with six.assertRaisesRegex(self, TypeError,
                                   'must match the type.*float.*DNA'):
            self.msa.append(42.0)
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_wrong_length(self):
        with six.assertRaisesRegex(
                self, ValueError,
                'must match the number of positions.*5 != 4'):
            self.msa.append(DNA('ACGTA'))
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_with_minter(self):
        to_append = DNA('', metadata={'id': 'c'})
        expected = TabularMSA(
            [DNA('', metadata={'id': 'a'}),
             DNA('', metadata={'id': 'b'}),
             to_append],
            minter='id')
        msa = TabularMSA([DNA('', metadata={'id': 'a'}),
                          DNA('', metadata={'id': 'b'})],
                         minter='id')
        msa.append(to_append, minter='id')
        self.assertEqual(msa, expected)

    def test_no_key_no_minter_msa_does_not_have_keys(self):
        self.msa.append(DNA('AAAA'))
        expected = TabularMSA([DNA('ACGT'), DNA('TGCA'), DNA('AAAA')])
        self.assertEqual(self.msa, expected)

    def test_no_key_no_minter_msa_has_keys(self):
        with six.assertRaisesRegex(self, OperationError,
                                   "MSA has keys but no key or minter was "
                                   "provided."):
            self.msa_with_keys.append(self.append_seq_with_keys)
        self.assertEqual(self.msa_with_keys, self.msa_with_keys_unmodified)

    def test_with_key_no_minter_msa_does_not_have_keys(self):
        with six.assertRaisesRegex(self, OperationError,
                                   "key was provided but MSA does not have "
                                   "keys"):
            self.msa.append(self.append_seq, key='')
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_with_key_no_minter_msa_has_keys(self):
        self.msa_with_keys.append(self.append_seq_with_keys,
                                  key=self.append_key)
        self.assertEqual(self.msa_with_keys, self.msa_with_keys_after_append)

    def test_no_key_with_minter_msa_does_not_have_keys(self):
        with six.assertRaisesRegex(self, OperationError,
                                   "minter was provided but MSA does not have "
                                   "keys"):
            self.msa.append(self.append_seq, minter='')
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_no_key_with_minter_msa_has_keys(self):
        self.msa_with_keys.append(self.append_seq_with_keys,
                                  minter=lambda seq: self.append_key)
        self.assertEqual(self.msa_with_keys, self.msa_with_keys_after_append)

    def test_with_key_and_minter_msa_does_not_have_keys(self):
        with six.assertRaisesRegex(self, ValueError, "both.*minter.*key"):
            self.msa.append(self.append_seq, key='', minter='')
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_with_key_and_minter_msa_has_keys(self):
        with six.assertRaisesRegex(self, ValueError, "both.*minter.*key"):
            self.msa_with_keys.append(self.append_seq_with_keys, key='',
                                      minter='')
        self.assertEqual(self.msa, self.msa_unmodified)

    def test_do_not_mutate_if_invalid_key(self):
        with six.assertRaisesRegex(self, TypeError, "unhashable.*dict"):
            self.msa_with_keys.append(self.append_seq_with_keys, key={})
        self.assertEqual(self.msa_with_keys, self.msa_with_keys_unmodified)


class TestGapFrequencies(unittest.TestCase):
    def test_default_behavior(self):
        msa = TabularMSA([DNA('AA.'),
                          DNA('-A-')])

        freqs = msa.gap_frequencies()

        npt.assert_array_equal(np.array([1, 0, 2]), freqs)

    def test_invalid_axis_str(self):
        with six.assertRaisesRegex(self, ValueError, "axis.*'foo'"):
            TabularMSA([]).gap_frequencies(axis='foo')

    def test_invalid_axis_int(self):
        with six.assertRaisesRegex(self, ValueError, "axis.*2"):
            TabularMSA([]).gap_frequencies(axis=2)

    def test_position_axis_str_and_int_equivalent(self):
        msa = TabularMSA([DNA('ACGT'),
                          DNA('A.G-'),
                          DNA('----')])

        str_freqs = msa.gap_frequencies(axis='position')
        int_freqs = msa.gap_frequencies(axis=1)

        npt.assert_array_equal(str_freqs, int_freqs)
        npt.assert_array_equal(np.array([0, 2, 4]), str_freqs)

    def test_sequence_axis_str_and_int_equivalent(self):
        msa = TabularMSA([DNA('ACGT'),
                          DNA('A.G-'),
                          DNA('----')])

        str_freqs = msa.gap_frequencies(axis='sequence')
        int_freqs = msa.gap_frequencies(axis=0)

        npt.assert_array_equal(str_freqs, int_freqs)
        npt.assert_array_equal(np.array([1, 2, 1, 2]), str_freqs)

    def test_correct_dtype_absolute_empty(self):
        msa = TabularMSA([])

        freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([]), freqs)
        self.assertEqual(int, freqs.dtype)

    def test_correct_dtype_relative_empty(self):
        msa = TabularMSA([])

        freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([]), freqs)
        self.assertEqual(float, freqs.dtype)

    def test_correct_dtype_absolute_non_empty(self):
        msa = TabularMSA([DNA('AC'),
                          DNA('-.')])

        freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([0, 2]), freqs)
        self.assertEqual(int, freqs.dtype)

    def test_correct_dtype_relative_non_empty(self):
        msa = TabularMSA([DNA('AC'),
                          DNA('-.')])

        freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([0.0, 1.0]), freqs)
        self.assertEqual(float, freqs.dtype)

    def test_no_sequences_absolute(self):
        msa = TabularMSA([])

        seq_freqs = msa.gap_frequencies(axis='sequence')
        pos_freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([]), seq_freqs)
        npt.assert_array_equal(np.array([]), pos_freqs)

    def test_no_sequences_relative(self):
        msa = TabularMSA([])

        seq_freqs = msa.gap_frequencies(axis='sequence', relative=True)
        pos_freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([]), seq_freqs)
        npt.assert_array_equal(np.array([]), pos_freqs)

    def test_no_positions_absolute(self):
        msa = TabularMSA([DNA('')])

        seq_freqs = msa.gap_frequencies(axis='sequence')
        pos_freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([]), seq_freqs)
        npt.assert_array_equal(np.array([0]), pos_freqs)

    def test_no_positions_relative(self):
        msa = TabularMSA([DNA('')])

        seq_freqs = msa.gap_frequencies(axis='sequence', relative=True)
        pos_freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([]), seq_freqs)
        npt.assert_array_equal(np.array([np.nan]), pos_freqs)

    def test_single_sequence_absolute(self):
        msa = TabularMSA([DNA('.T')])

        seq_freqs = msa.gap_frequencies(axis='sequence')
        pos_freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([1, 0]), seq_freqs)
        npt.assert_array_equal(np.array([1]), pos_freqs)

    def test_single_sequence_relative(self):
        msa = TabularMSA([DNA('.T')])

        seq_freqs = msa.gap_frequencies(axis='sequence', relative=True)
        pos_freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([1.0, 0.0]), seq_freqs)
        npt.assert_array_equal(np.array([0.5]), pos_freqs)

    def test_single_position_absolute(self):
        msa = TabularMSA([DNA('.'),
                          DNA('T')])

        seq_freqs = msa.gap_frequencies(axis='sequence')
        pos_freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([1]), seq_freqs)
        npt.assert_array_equal(np.array([1, 0]), pos_freqs)

    def test_single_position_relative(self):
        msa = TabularMSA([DNA('.'),
                          DNA('T')])

        seq_freqs = msa.gap_frequencies(axis='sequence', relative=True)
        pos_freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([0.5]), seq_freqs)
        npt.assert_array_equal(np.array([1.0, 0.0]), pos_freqs)

    def test_position_axis_absolute(self):
        msa = TabularMSA([
                DNA('ACGT'),   # no gaps
                DNA('A.G-'),   # some gaps (mixed gap chars)
                DNA('----'),   # all gaps
                DNA('....')])  # all gaps

        freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([0, 2, 4, 4]), freqs)

    def test_position_axis_relative(self):
        msa = TabularMSA([DNA('ACGT'),
                          DNA('A.G-'),
                          DNA('CCC.'),
                          DNA('----'),
                          DNA('....')])

        freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([0.0, 0.5, 0.25, 1.0, 1.0]), freqs)

    def test_sequence_axis_absolute(self):
        msa = TabularMSA([DNA('AC-.'),
                          DNA('A.-.'),
                          DNA('G--.')])

        freqs = msa.gap_frequencies(axis='sequence')

        npt.assert_array_equal(np.array([0, 2, 3, 3]), freqs)

    def test_sequence_axis_relative(self):
        msa = TabularMSA([DNA('AC--.'),
                          DNA('A.A-.'),
                          DNA('G-A-.')])

        freqs = msa.gap_frequencies(axis='sequence', relative=True)

        npt.assert_array_equal(np.array([0.0, 2/3, 1/3, 1.0, 1.0]), freqs)

    def test_relative_frequencies_precise(self):
        class CustomSequence(IUPACSequence):
            @classproperty
            @overrides(IUPACSequence)
            def gap_chars(cls):
                return set('0123456789')

            @classproperty
            @overrides(IUPACSequence)
            def nondegenerate_chars(cls):
                return set('')

            @classproperty
            @overrides(IUPACSequence)
            def degenerate_map(cls):
                return {}

        msa = TabularMSA([CustomSequence('0123456789')])

        freqs = msa.gap_frequencies(axis='position', relative=True)

        npt.assert_array_equal(np.array([1.0]), freqs)

    def test_custom_gap_characters(self):
        class CustomSequence(IUPACSequence):
            @classproperty
            @overrides(IUPACSequence)
            def gap_chars(cls):
                return set('#$*')

            @classproperty
            @overrides(IUPACSequence)
            def nondegenerate_chars(cls):
                return set('ABC-.')

            @classproperty
            @overrides(IUPACSequence)
            def degenerate_map(cls):
                return {'D': 'ABC-.'}

        msa = TabularMSA([CustomSequence('ABCD'),
                          CustomSequence('-.-.'),
                          CustomSequence('A#C*'),
                          CustomSequence('####'),
                          CustomSequence('$$$$')])

        freqs = msa.gap_frequencies(axis='position')

        npt.assert_array_equal(np.array([0, 0, 2, 4, 4]), freqs)


class TestIsSequenceAxis(unittest.TestCase):
    def setUp(self):
        self.msa = TabularMSA([])

    def test_invalid_str(self):
        with six.assertRaisesRegex(self, ValueError, "axis.*'foo'"):
            self.msa._is_sequence_axis('foo')

    def test_invalid_int(self):
        with six.assertRaisesRegex(self, ValueError, "axis.*2"):
            self.msa._is_sequence_axis(2)

    def test_positive_str(self):
        self.assertTrue(self.msa._is_sequence_axis('sequence'))

    def test_positive_int(self):
        self.assertTrue(self.msa._is_sequence_axis(0))

    def test_negative_str(self):
        self.assertFalse(self.msa._is_sequence_axis('position'))

    def test_negative_int(self):
        self.assertFalse(self.msa._is_sequence_axis(1))


if __name__ == "__main__":
    unittest.main()