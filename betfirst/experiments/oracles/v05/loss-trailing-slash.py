from solution import route_equal
assert route_equal('/api/','/api')
assert route_equal('/api/','/api/')
assert not route_equal('/apix','/api')
assert route_equal('/','/')
