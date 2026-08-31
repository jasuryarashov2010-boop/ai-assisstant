from app.utils.html import bar

def test_bar():
    assert bar(0,100)=='░░░░░░░░░░'
    assert bar(50,100)=='█████░░░░░'
