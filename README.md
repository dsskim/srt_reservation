# Python program for booking SRT ticket.


매진된 SRT 표의 예매를 도와주는 파이썬 프로그램입니다.  
원하는 표가 나올 때 까지 새로고침하여 예약을 시도합니다.


## 다운
```cmd
git clone https://github.com/kminito/srt_reservation.git
```
  
## 필요
- 파이썬 3.7, 3.9에서 테스트 했습니다.

```py
pip install -r requirements.txt
```


## Arguments
    dpt: SRT 출발역
    arr: SRT 도착역
    dt: 출발 날짜 YYYYMMDD 형태 ex) 20220115
    tm: 출발 시간 hh 형태, 반드시 짝수 ex) 06, 08, 14, ...
    num: 검색 결과 중 예약 가능 여부 확인할 기차의 수 (default : 2)
    reserve: 예약 대기가 가능할 경우 선택 여부 (default : False)

    station_list = ["수서", "동탄", "평택지제", "천안아산", "오송", "대전", "김천(구미)", "동대구",
    "신경주", "울산(통도사)", "부산", "공주", "익산", "정읍", "광주송정", "나주", "목포"]



## 간단 사용법

회원번호 1234567890  
비밀번호 000000  
동탄 -> 동대구, 2022년 01월 17일 오전 8시 이후 기차  
검색 결과 중 상위 2개가 예약 가능할 경우 예약

```cmd
python quickstart.py --user 1234567890 --psw 000000 --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08
```

**Optional**  
예약대기 사용 및 검색 결과 상위 3개의 예약 가능 여부 확인
```cmd
python quickstart.py --user 1234567890 --psw 000000 --dpt 동탄 --arr 동대구 --dt 20220117 --tm 08 --num 3 --reserve True
```

**실행 결과**

![](./img/img1.png)

## 웹 UI 사용법

웹 인터페이스를 통해 더 쉽게 SRT 예약을 할 수 있습니다.

### 웹 UI 실행하기

```cmd
python app.py
```

위 명령어를 실행하면 Flask 웹 서버가 시작되고, 브라우저에서 `http://localhost:5000`으로 접속할 수 있습니다.

### 웹 UI 사용 방법

1. 웹 브라우저에서 `http://localhost:5000`에 접속합니다.
2. 로그인 정보(아이디, 비밀번호)를 입력합니다.
3. 출발역, 도착역, 출발 날짜, 출발 시간을 선택합니다.
4. 검색할 기차 수와 예약 대기 신청 여부를 설정합니다.
5. '예약 시작' 버튼을 클릭하면 백그라운드에서 예약 프로세스가 시작됩니다.
6. 예약 상태 페이지에서 실시간으로 진행 상황을 확인할 수 있습니다.

![웹 UI 예시](./img/web_ui.png)

## 기타  
명절 승차권 예약에는 사용이 불가합니다.
