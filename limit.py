import requests
import json

class IpTimeController:
    def __init__(self):
        self.base_url = "http://192.168.4.1"
        self.api_url = f"{self.base_url}/cgi/service.cgi"
        self.username = "admin"
        self.password = "emdeo1004"
        self.session = requests.Session()
        # ipTIME 신규 UI 통신을 위한 기본 헤더
        self.session.headers.update({
            "Content-Type": "application/json; charset=UTF-8",
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

    def login(self):
        """AX3000M 관리자 로그인 및 세션 쿠키(efm_session_id) 획득"""
        payload = {
            "method": "session/login",
            "params": {
                "id": self.username,
                "pw": self.password
            }
        }
        try:
            response = self.session.post(self.api_url, data=json.dumps(payload), timeout=5)
            res_json = response.json()
            if response.status_code == 200 and res_json.get("result"):
                print("[성공] AX3000M (192.168.4.1) 로그인 완료!")
                return True
            else:
                print(f"[실패] 로그인 거부: {res_json}")
                return False
        except Exception as e:
            print(f"[오류] 공유기 접속 실패: {e}")
            return False

    def disconnect_easymesh_station(self, mac_address):
        """EasyMesh Station Info의 [Disconnect] 버튼 기능 호출"""
        payload = {
            "method": "mesh/station/disconnect", # 펌웨어 빌드에 따라 패킷 확인 필요
            "params": {
                "mac": mac_address
            }
        }
        response = self.session.post(self.api_url, data=json.dumps(payload))
        return response.json()

if __name__ == "__main__":
    controller = IpTimeController()
    controller.login()