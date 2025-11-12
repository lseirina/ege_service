from fastapi.testclient import TestClient
from main import app


client = TestClient(app)

class TestEgeAPI:
    """Test for API ege service."""
    
    def test_register_student(self):
        response = client.post("/students/50000/Тестовый")
        assert response.status_code == 200
    
    def test_get_subjects(self):
        """TEst getting students subjects"""
        response = client.get("/subjects")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        expected_subjects = ["Математика", "Русский язык", "Информатика"]
        for subject in expected_subjects:
            assert subject in data
    
    def test_registration_student_error(self):
        """Student registration returns error."""
        client.post('/students/10001/Петров')
        response = client.post('/students/10001/Петров')
        
        assert response.status_code == 200
        assert response.json() == "error" 
    
    def test_health_check(self):
        """Тест health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "database" in data
        assert data["status"] in ["healthy", "unhealthy"]
        
    
            
        
    