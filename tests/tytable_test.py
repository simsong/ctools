# Some tests for tytable


from ctools.tytable import ttable, tytable

def test_ttable():
    a = ttable()
    a.add_head(['Head One','Head Two'])
    a.add_data([1,2])
    a.add_data(['foo','bar'])
    print( a.typeset(mode=a.LATEX ))
    print( a.typeset(mode=a.HTML ))

    a.add_data(['foo','bar'],annotations=['\\cellcolor{blue}',''])
    assert 'blue' in a.typeset(mode=a.LATEX)

def test_tytable():
    a = tytable()
    a.add_row('td', [1,2,3])
    a.add_row('td', ['a','b','c'])
    a.add_row('td', [1,2,3,4])
    a.add_row('td', ['a','b','c','d','e'])
    assert a.nrows()==4
    assert a.ncols()==4
    
