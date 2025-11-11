import pytest
from fastapi.testclient import Testclient
from main import app


client = TestClient(app)


class TestEgeAPI:
    def test_register_student_success(self):
        "Students registration is successfull"
        response = client.post("/students/10000/Иванов")
        
        assert response.status_code == 200
        assert response.text = "ok"
        
    def test_registration_student_error(self):
        "Student registartion returnd error."
        client.post('/students/10001/Петров')
        response = client.post('/students/10001/Петров')
        
        assert response.status_code == 200
        assert response.text == "error"