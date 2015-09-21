
import pytest

from boltons.iterutils import first, remap, default_enter, default_exit
from boltons.dictutils import OMD


isbool = lambda x: isinstance(x, bool)
isint = lambda x: isinstance(x, int)
odd = lambda x: isint(x) and x % 2 != 0
even = lambda x: isint(x) and x % 2 == 0
is_meaning_of_life = lambda x: x == 42


class TestFirst(object):
    def test_empty_iterables(self):
        """
        Empty iterables return None.
        """
        s = set()
        l = []
        assert first(s) is None
        assert first(l) is None

    def test_default_value(self):
        """
        Empty iterables + a default value return the default value.
        """
        s = set()
        l = []
        assert first(s, default=42) == 42
        assert first(l, default=3.14) == 3.14

        l = [0, False, []]
        assert first(l, default=3.14) == 3.14

    def test_selection(self):
        """
        Success cases with and without a key function.
        """
        l = [(), 0, False, 3, []]

        assert first(l, default=42) == 3
        assert first(l, key=isint) == 0
        assert first(l, key=isbool) is False
        assert first(l, key=odd) == 3
        assert first(l, key=even) == 0
        assert first(l, key=is_meaning_of_life) is None


class TestRemap(object):
    # TODO: test enter return (prepopulated_collection, False)
    # TODO: test which counts the number of visit calls
    # TODO: test namedtuples and other immutable containers

    def test_basic_clone(self):
        orig = {"a": "b", "c": [1, 2]}
        assert orig == remap(orig)

        orig2 = [{1: 2}, {"a": "b", "c": [1, 2, {"cat": "dog"}]}]
        assert orig2 == remap(orig2)

    def test_empty(self):
        assert [] == remap([])
        assert {} == remap({})
        assert set() == remap(set())

    def test_unremappable(self):
        obj = object()
        with pytest.raises(TypeError):
            remap(obj)

    def test_basic_upper(self):
        orig = {'a': 1, 'b': object(), 'c': {'d': set()}}
        remapped = remap(orig, lambda p, k, v: (k.upper(), v))
        assert orig['a'] == remapped['A']
        assert orig['b'] == remapped['B']
        assert orig['c']['d'] == remapped['C']['D']

    def test_item_drop(self):
        orig = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        even_items = remap(orig, lambda p, k, v: not (v % 2))
        assert even_items == [0, 2, 4, 6, 8]

    def test_noncallables(self):
        with pytest.raises(TypeError):
            remap([], visit='test')
        with pytest.raises(TypeError):
            remap([], enter='test')
        with pytest.raises(TypeError):
            remap([], exit='test')

    def test_sub_selfref(self):
        coll = [0, 1, 2, 3]
        sub = []
        sub.append(sub)
        coll.append(sub)
        with pytest.raises(RuntimeError):
            # if equal, should recurse infinitely
            assert coll == remap(coll)

    def test_root_selfref(self):
        selfref = [0, 1, 2, 3]
        selfref.append(selfref)
        with pytest.raises(RuntimeError):
            assert selfref == remap(selfref)

        selfref2 = {}
        selfref2['self'] = selfref2
        with pytest.raises(RuntimeError):
            assert selfref2 == remap(selfref2)

    def test_duperef(self):
        val = ['hello']
        duperef = [val, val]
        remapped = remap(duperef)
        assert remapped[0] is remapped[1]
        assert remapped[0] is not duperef[0]

    def test_path(self):
        path_map = {}

        # test visit's path
        target_str = 'test'
        orig = [[[target_str]]]
        ref_path = (0, 0, 0)

        def visit(path, key, value):
            if value is target_str:
                path_map['target_str'] = path + (key,)
            return key, value

        remapped = remap(orig, visit=visit)

        assert remapped == orig
        assert path_map['target_str'] == ref_path

        # test enter's path
        target_obj = object()
        orig = {'a': {'b': {'c': {'d': ['e', target_obj, 'f']}}}}
        ref_path = ('a', 'b', 'c', 'd', 1)

        def enter(path, key, value):
            if value is target_obj:
                path_map['target_obj'] = path + (key,)
            return default_enter(path, key, value)

        remapped = remap(orig, enter=enter)

        assert remapped == orig
        assert path_map['target_obj'] == ref_path

        # test exit's path
        target_set = frozenset([1, 7, 3, 8])
        orig = [0, 1, 2, [3, 4, [5, target_set]]]
        ref_path = (3, 2, 1)

        # TODO: reverse order of new_items, new_parent
        def exit(path, key, old_parent, new_parent, new_items):
            if old_parent is target_set:
                path_map['target_set'] = path + (key,)
            return default_exit(path, key, old_parent, new_parent, new_items)

        remapped = remap(orig, exit=exit)

        assert remapped == orig
        assert path_map['target_set'] == ref_path

    def test_reraise_visit(self):
        root = {'A': 'b', 1: 2}
        key_to_lower = lambda p, k, v: (k.lower(), v)
        with pytest.raises(AttributeError):
            remap(root, key_to_lower)

        remapped = remap(root, key_to_lower, reraise_visit=False)
        assert remapped['a'] == 'b'
        assert remapped[1] == 2

    def test_drop_nones(self):
        orig = {'a': 1, 'b': None, 'c': [3, None, 4, None]}
        ref = {'a': 1, 'c': [3, 4]}
        drop_none = lambda p, k, v: v is not None
        remapped = remap(orig, visit=drop_none)
        assert remapped == ref

        orig = [None] * 100
        remapped = remap(orig, drop_none)
        assert not remapped

    def test_dict_to_omd(self):
        def enter(path, key, value):
            if isinstance(value, dict):
                return OMD(), sorted(value.items())
            return default_enter(path, key, value)

        orig = [{'title': 'Wild Palms',
                 'ratings': {1: 1, 2: 3, 3: 5, 4: 6, 5: 3}},
                {'title': 'Twin Peaks',
                 'ratings': {1: 3, 2: 2, 3: 8, 4: 12, 5: 15}}]
        remapped = remap(orig, enter=enter)
        assert remapped == orig

        assert isinstance(remapped[0], OMD)
        assert isinstance(remapped[0]['ratings'], OMD)
        assert isinstance(remapped[1], OMD)
        assert isinstance(remapped[1]['ratings'], OMD)

    def test_sort_all_lists(self):
        def exit(path, key, old_parent, new_parent, new_items):
            # NB: in this case, I'd normally use *a, **kw
            ret = default_exit(path, key, old_parent, new_parent, new_items)
            if isinstance(ret, list):
                ret.sort()
            return ret

        # NB: Airplane model numbers (Boeing and Airbus)
        orig = [[[7, 0, 7],
                 [7, 2, 7],
                 [7, 7, 7],
                 [7, 3, 7]],
                [[3, 8, 0],
                 [3, 2, 0],
                 [3, 1, 9],
                 [3, 5, 0]]]
        ref = [[[0, 2, 3],
                [0, 3, 5],
                [0, 3, 8],
                [1, 3, 9]],
               [[0, 7, 7],
                [2, 7, 7],
                [3, 7, 7],
                [7, 7, 7]]]

        remapped = remap(orig, exit=exit)
        assert remapped == ref

    def test_collector_pattern(self):
        all_interests = set()

        def enter(path, key, value):
            try:
                all_interests.update(value['interests'])
            except:
                pass
            return default_enter(path, key, value)

        orig = [{'name': 'Kate',
                 'interests': ['theater', 'manga'],
                 'dads': [{'name': 'Chris',
                           'interests': ['biking', 'python']}]},
                {'name': 'Avery',
                 'interests': ['museums', 'pears'],
                 'dads': [{'name': 'Kurt',
                           'interests': ['python', 'recursion']}]}]

        ref = set(['python', 'recursion', 'biking', 'museums',
                   'pears', 'theater', 'manga'])

        remap(orig, enter=enter)
        assert all_interests == ref

    def test_add_length(self):
        def exit(path, key, old_parent, new_parent, new_items):
            ret = default_exit(path, key, old_parent, new_parent, new_items)
            try:
                ret['review_length'] = len(ret['review'])
            except:
                pass
            return ret

        orig = {'Star Trek':
                {'TNG': {'stars': 10,
                         'review': "Episodic AND deep. <3 Data."},
                 'DS9': {'stars': 8.5,
                         'review': "Like TNG, but with a story and no Data."},
                 'ENT': {'stars': None,
                         'review': "Can't review what you can't watch."}},
                'Babylon 5': {'stars': 6,
                              'review': "Sophomoric, like a bitter laugh."},
                'Dr. Who': {'stars': None,
                            'review': "800 episodes is too many to review."}}
        remapped = remap(orig, exit=exit)
        assert (remapped['Star Trek']['TNG']['review_length']
                < remapped['Star Trek']['DS9']['review_length'])

    def test_prepop(self):
        """Demonstrating normalization and ID addition through prepopulating
        the objects wth an enter callback.
        """
        base_obj = {'name': None,
                    'rank': None,
                    'id': 1}

        def enter(path, key, value):
            new_parent, new_items = default_enter(path, key, value)
            try:
                new_parent.update(base_obj)
                base_obj['id'] += 1
            except:
                pass
            return new_parent, new_items

        orig = [{'name': 'Firefox', 'rank': 1},
                {'name': 'Chrome', 'rank': 2},
                {'name': 'IE'}]
        ref = [{'name': 'Firefox', 'rank': 1, 'id': 1},
               {'name': 'Chrome', 'rank': 2, 'id': 2},
               {'name': 'IE', 'rank': None, 'id': 3}]
        remapped = remap(orig, enter=enter)
        assert remapped == ref