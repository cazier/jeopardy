import pytest

from jeopardy import alex

def test_content_creation():
    data = {"answer": "answer", "question": "question", "value": 200, "date": "1992-08-13"}
    content = alex.Content(details = data, category_index= 0)

    assert content.value == data['value']

    assert content.id() == '0_200'
    assert content.shown == False

    assert content.get() == {"answer": "answer", "question": "question", "wager": False, "year": "1992"}

    assert content.shown == True

    class Sample(object):
        value = 300
    
    sample = Sample()

    assert content < sample