from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, ValidationError
import threading
import os
import uuid
import json
from datetime import datetime
import atexit

from srt_reservation.main import SRT
from srt_reservation.validation import station_list

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# 데이터 저장 경로
DATA_FILE = 'reservation_tasks.json'

# 예약 작업 목록을 저장할 딕셔너리
reservation_tasks = {}

# 프로그램 종료 시 작업 목록 저장
def save_tasks():
    # 저장할 데이터 준비 (스레드 객체는 저장할 수 없으므로 제외)
    save_data = {}
    for task_id, task in reservation_tasks.items():
        if task['thread'] and task['thread'].is_alive():
            # 실행 중인 작업만 저장
            save_data[task_id] = {
                'login_id': task['login_id'],
                'dpt_stn': task['dpt_stn'],
                'arr_stn': task['arr_stn'],
                'dpt_dt': task['dpt_dt'],
                'dpt_tm': task['dpt_tm'],
                'num_trains_to_check': task['num_trains_to_check'],
                'want_reserve': task['want_reserve'],
                'is_running': task['is_running'],
                'message': task['message'],
                'refresh_count': task['refresh_count'],
                'is_booked': task['is_booked'],
                'created_at': task['created_at']
            }
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False)

# 프로그램 시작 시 작업 목록 로드
def load_tasks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                saved_tasks = json.load(f)
                
            for task_id, task_data in saved_tasks.items():
                # 비밀번호는 저장하지 않으므로 None으로 설정
                login_psw = None
                
                # 작업 재시작
                if task_data['is_running'] and not task_data['is_booked']:
                    task_data['message'] = '세션이 종료되어 예약이 중단되었습니다. 다시 시작하려면 재시작 버튼을 클릭하세요.'
                    task_data['is_running'] = False
                
                # 스레드는 None으로 초기화
                task_data['thread'] = None
                
                # 작업 목록에 추가
                reservation_tasks[task_id] = task_data
        except Exception as e:
            print(f"작업 로드 중 오류 발생: {str(e)}")

# 프로그램 종료 시 작업 목록 저장
atexit.register(save_tasks)

class SRTForm(FlaskForm):
    login_id = StringField('아이디', validators=[DataRequired()])
    login_psw = PasswordField('비밀번호', validators=[DataRequired()])
    dpt_stn = SelectField('출발역', choices=[(stn, stn) for stn in station_list], validators=[DataRequired()])
    arr_stn = SelectField('도착역', choices=[(stn, stn) for stn in station_list], validators=[DataRequired()])
    dpt_dt = StringField('출발 날짜 (YYYYMMDD)', validators=[DataRequired(), Length(min=8, max=8)])
    dpt_tm = StringField('출발 시간 (hh)', validators=[DataRequired(), Length(min=2, max=2)])
    num_trains_to_check = IntegerField('검색할 기차 수', default=2)
    want_reserve = BooleanField('예약 대기 신청')
    submit = SubmitField('예약 시작')
    
    def validate_dpt_dt(self, field):
        try:
            datetime.strptime(field.data, '%Y%m%d')
        except ValueError:
            raise ValidationError('날짜 형식이 올바르지 않습니다. YYYYMMDD 형식으로 입력해주세요.')
    
    def validate_dpt_tm(self, field):
        try:
            hour = int(field.data)
            if hour < 0 or hour > 23 or hour % 2 != 0:
                raise ValidationError('시간은 짝수 시간만 입력 가능합니다 (0, 2, 4, ..., 22)')
        except ValueError:
            raise ValidationError('시간 형식이 올바르지 않습니다. hh 형식으로 입력해주세요.')

def run_srt_reservation(task_id, login_id, login_psw, dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check, want_reserve):
    task = reservation_tasks[task_id]
    
    task['is_running'] = True
    task['message'] = '예약을 시작합니다...'
    task['refresh_count'] = 0
    task['is_booked'] = False
    
    try:
        srt = SRT(dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check, want_reserve)
        
        # SRT 클래스의 refresh_result 메서드를 오버라이드하여 상태 업데이트
        original_refresh_result = srt.refresh_result
        def new_refresh_result():
            # 작업이 중지되었는지 확인
            if task_id not in reservation_tasks or not reservation_tasks[task_id]['is_running']:
                raise Exception("작업이 사용자에 의해 중지되었습니다.")
                
            task['refresh_count'] += 1
            task['message'] = f'새로고침 {task["refresh_count"]}회 시도 중...'
            return original_refresh_result()
        srt.refresh_result = new_refresh_result
        
        # 예약 완료 확인 메서드 오버라이드
        original_check_result = srt.check_result
        def new_check_result():
            result = original_check_result()
            if srt.is_booked:
                task['is_booked'] = True
                task['message'] = '예약이 완료되었습니다!'
            return result
        srt.check_result = new_check_result
        
        srt.run(login_id, login_psw)
        
    except Exception as e:
        task['message'] = f'오류 발생: {str(e)}'
    finally:
        task['is_running'] = False

@app.route('/', methods=['GET', 'POST'])
def index():
    form = SRTForm()
    
    if form.validate_on_submit():
        # 폼 데이터 가져오기
        login_id = form.login_id.data
        login_psw = form.login_psw.data
        dpt_stn = form.dpt_stn.data
        arr_stn = form.arr_stn.data
        dpt_dt = form.dpt_dt.data
        dpt_tm = form.dpt_tm.data
        num_trains_to_check = form.num_trains_to_check.data
        want_reserve = form.want_reserve.data
        
        # 새 작업 ID 생성
        task_id = str(uuid.uuid4())
        
        # 작업 정보 저장
        reservation_tasks[task_id] = {
            'login_id': login_id,
            'dpt_stn': dpt_stn,
            'arr_stn': arr_stn,
            'dpt_dt': dpt_dt,
            'dpt_tm': dpt_tm,
            'num_trains_to_check': num_trains_to_check,
            'want_reserve': want_reserve,
            'is_running': False,
            'message': '예약 준비 중...',
            'refresh_count': 0,
            'is_booked': False,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'thread': None
        }
        
        # 백그라운드에서 예약 실행
        thread = threading.Thread(
            target=run_srt_reservation,
            args=(task_id, login_id, login_psw, dpt_stn, arr_stn, dpt_dt, dpt_tm, num_trains_to_check, want_reserve)
        )
        thread.daemon = True
        thread.start()
        
        # 스레드 객체 저장
        reservation_tasks[task_id]['thread'] = thread
        
        flash('예약 작업이 시작되었습니다.')
        return redirect(url_for('index'))
    
    return render_template('index.html', form=form, tasks=reservation_tasks)

@app.route('/tasks')
def tasks():
    return redirect(url_for('index'))

@app.route('/status/<task_id>')
def status(task_id):
    if task_id not in reservation_tasks:
        flash('존재하지 않는 작업입니다.')
        return redirect(url_for('tasks'))
        
    return render_template('status.html', task=reservation_tasks[task_id], task_id=task_id)

@app.route('/api/status/<task_id>')
def api_status(task_id):
    if task_id not in reservation_tasks:
        return jsonify({'error': '존재하지 않는 작업입니다.'}), 404
        
    task = reservation_tasks[task_id]
    return jsonify({
        'is_running': task['is_running'],
        'message': task['message'],
        'refresh_count': task['refresh_count'],
        'is_booked': task['is_booked']
    })

@app.route('/api/tasks')
def api_tasks():
    tasks_data = {}
    for task_id, task in reservation_tasks.items():
        tasks_data[task_id] = {
            'login_id': task['login_id'],
            'dpt_stn': task['dpt_stn'],
            'arr_stn': task['arr_stn'],
            'dpt_dt': task['dpt_dt'],
            'dpt_tm': task['dpt_tm'],
            'is_running': task['is_running'],
            'message': task['message'],
            'refresh_count': task['refresh_count'],
            'is_booked': task['is_booked'],
            'created_at': task['created_at']
        }
    return jsonify(tasks_data)

@app.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    if task_id not in reservation_tasks:
        return jsonify({'success': False, 'message': '존재하지 않는 작업입니다.'}), 404
        
    task = reservation_tasks[task_id]
    task['is_running'] = False
    task['message'] = '사용자에 의해 취소되었습니다.'
    
    return jsonify({'success': True})

@app.route('/restart/<task_id>', methods=['POST'])
def restart_task(task_id):
    if task_id not in reservation_tasks:
        return jsonify({'success': False, 'message': '존재하지 않는 작업입니다.'}), 404
        
    task = reservation_tasks[task_id]
    
    # 이미 실행 중인 경우
    if task['is_running']:
        return jsonify({'success': False, 'message': '이미 실행 중인 작업입니다.'}), 400
        
    # 비밀번호가 필요함
    return jsonify({'success': True, 'need_password': True})

@app.route('/do_restart/<task_id>', methods=['POST'])
def do_restart_task(task_id):
    if task_id not in reservation_tasks:
        return jsonify({'success': False, 'message': '존재하지 않는 작업입니다.'}), 404
        
    task = reservation_tasks[task_id]
    
    # 이미 실행 중인 경우
    if task['is_running']:
        return jsonify({'success': False, 'message': '이미 실행 중인 작업입니다.'}), 400
        
    # 비밀번호 가져오기
    login_psw = request.json.get('password')
    if not login_psw:
        return jsonify({'success': False, 'message': '비밀번호를 입력해주세요.'}), 400
    
    # 백그라운드에서 예약 실행
    thread = threading.Thread(
        target=run_srt_reservation,
        args=(
            task_id, 
            task['login_id'], 
            login_psw, 
            task['dpt_stn'], 
            task['arr_stn'], 
            task['dpt_dt'], 
            task['dpt_tm'], 
            task['num_trains_to_check'], 
            task['want_reserve']
        )
    )
    thread.daemon = True
    thread.start()
    
    # 스레드 객체 저장
    task['thread'] = thread
    
    return jsonify({'success': True})

@app.route('/delete/<task_id>', methods=['POST'])
def delete_task(task_id):
    if task_id not in reservation_tasks:
        return jsonify({'success': False, 'message': '존재하지 않는 작업입니다.'}), 404
        
    # 실행 중인 경우 먼저 중지
    task = reservation_tasks[task_id]
    task['is_running'] = False
    
    # 작업 목록에서 제거
    del reservation_tasks[task_id]
    
    return jsonify({'success': True})

if __name__ == '__main__':
    # templates 폴더가 없으면 생성
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # 저장된 작업 로드
    load_tasks()
    
    app.run(debug=True, host='0.0.0.0', port=5000) 