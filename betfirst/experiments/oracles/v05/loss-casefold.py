from solution import same_user
assert same_user('Alice','alice')
assert same_user('ALICE','alice')
assert not same_user('alice ','alice')
assert not same_user('a-lice','alice')
