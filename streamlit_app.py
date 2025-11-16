import streamlit as st
import random
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# 페이지 설정
st.set_page_config(page_title="Where is the bookstore?", layout="wide")

# 건물 정보 (도로 그리드 좌표 - 가로 9개, 세로 7개 교차점)
# 각 건물은 도로 교차점 좌표로 표현 (row: 0-6, col: 0-8)
# 건물들은 교차로 사이에 위치하므로, 차량은 교차로를 따라 이동
buildings = {
    "Megi cafe": (1, 1),
    "Nolbu's House": (1, 3),
    "Heung-bu House": (1, 5),
    "Choco House": (1, 7),
    "GYM": (2, 1),
    "SCHOOL": (2, 3),
    "MARKET": (2, 5),
    "Cafe Juny": (2, 7),
    "Andy's House": (3, 1),
    "집게리아": (3, 3),
    "Chicken house": (3, 5),
    "BUS STOP": (3, 7),
    "OLIVE": (4, 1),
    "Park": (4, 3),
    "DU": (4, 5),
    "Hospital": (4, 7),
    "Apartment": (5, 1),
    "Book Store": (5, 3),
    "Brown House": (5, 5),
    "Pink House": (5, 7),
    "Church": (6, 1),
    "Candy Shop": (6, 3),
    "MUSEUM": (6, 5),
    "RIVER": (6, 7),
}

# 도로 연결 정보 (각 교차로에서 갈 수 있는 방향)
# 방향: 0=북, 1=동, 2=남, 3=서
# 가로 9개(0-8), 세로 7개(0-6) 교차점
road_connections = {}
for row in range(7):
    for col in range(9):
        connections = []
        if row > 0:  # 북쪽으로 갈 수 있음
            connections.append(0)
        if col < 8:  # 동쪽으로 갈 수 있음
            connections.append(1)
        if row < 6:  # 남쪽으로 갈 수 있음
            connections.append(2)
        if col > 0:  # 서쪽으로 갈 수 있음
            connections.append(3)
        road_connections[(row, col)] = connections

# 세션 상태 초기화
if 'start' not in st.session_state:
    start_building = random.choice(list(buildings.keys()))
    destinations = [b for b in buildings.keys() if b != start_building]
    end_building = random.choice(destinations)
    
    st.session_state.start = start_building
    st.session_state.end = end_building
    st.session_state.current_pos = buildings[start_building]
    st.session_state.direction = 1  # 0=북, 1=동, 2=남, 3=서 (시작은 동쪽)
    st.session_state.moves = []
    st.session_state.completed = False
    st.session_state.message = ""

# 방향 벡터
direction_vectors = {
    0: (-1, 0),  # 북
    1: (0, 1),   # 동
    2: (1, 0),   # 남
    3: (0, -1),  # 서
}

direction_names = {
    0: "North ↑",
    1: "East →",
    2: "South ↓",
    3: "West ←"
}

def get_new_direction(current_dir, action):
    """행동에 따른 새 방향 계산"""
    if action == "turn_right":
        return (current_dir + 1) % 4
    elif action == "turn_left":
        return (current_dir - 1) % 4
    return current_dir

def move_forward(pos, direction):
    """현재 방향으로 한 칸 전진 (도로를 따라 1칸씩 이동)"""
    drow, dcol = direction_vectors[direction]
    # 교차로 사이를 이동하므로 1칸씩 이동
    new_pos = (pos[0] + drow * 1, pos[1] + dcol * 1)
    # 맵 범위 체크 (가로 0-8, 세로 0-6)
    if 0 <= new_pos[0] <= 6 and 0 <= new_pos[1] <= 8:
        return new_pos
    return pos

def check_near_destination():
    """목적지의 바로 위(북) 또는 바로 아래(남)에 있거나 같은 위치인지 확인"""
    end_pos = buildings[st.session_state.end]
    current_pos = st.session_state.current_pos
    
    # 같은 열에 있거나 같은 위치면 활성화
    same_col = (current_pos[1] == end_pos[1])
    same_position = (current_pos == end_pos)
    
    return same_col or same_position

# 지도 이미지 로드 및 차량 표시 함수
def create_map_with_car(image_path, current_pos, direction, destination):
    """지도 이미지에 차량 아이콘을 그려서 반환"""
    try:
        # 이미지 열기
        img = Image.open(image_path)
        img = img.copy()
        draw = ImageDraw.Draw(img)
        
        # 이미지 크기
        width, height = img.size
        
        # 도로 그리드 계산 (가로 9개, 세로 7개 교차점)
        grid_width = width / 8  # 8개 간격
        grid_height = height / 6  # 6개 간격
        
        # 현재 위치의 픽셀 좌표 계산 (도로 교차점)
        row, col = current_pos
        x = int(col * grid_width)
        y = int(row * grid_height)
        
        # 방향에 따른 삼각형 그리기 (차량 모양) - 크기 증가
        size = min(grid_width, grid_height) * 0.35
        
        if direction == 0:  # 북쪽 (위)
            points = [(x, y - size), (x - size/2, y + size/2), (x + size/2, y + size/2)]
        elif direction == 1:  # 동쪽 (오른쪽)
            points = [(x + size, y), (x - size/2, y - size/2), (x - size/2, y + size/2)]
        elif direction == 2:  # 남쪽 (아래)
            points = [(x, y + size), (x - size/2, y - size/2), (x + size/2, y - size/2)]
        else:  # 서쪽 (왼쪽)
            points = [(x - size, y), (x + size/2, y - size/2), (x + size/2, y + size/2)]
        
        # 차량 그리기 (빨간색 삼각형)
        draw.polygon(points, fill='red', outline='darkred')
        
        # 산타 이미지를 삼각형 중앙에 추가
        try:
            # 산타 이미지 로드 (상대 경로)
            santa_path = os.path.join(os.path.dirname(__file__), "santa emoji.jpg")
            santa_img = Image.open(santa_path)
            
            # 이미지 크기 조정
            emoji_size = int(size * 0.7)
            santa_img = santa_img.resize((emoji_size, emoji_size), Image.Resampling.LANCZOS)
            
            # 이미지를 중앙에 붙이기 위한 위치 계산
            paste_x = int(x - emoji_size / 2)
            paste_y = int(y - emoji_size / 2)
            
            # 투명도 처리를 위해 RGBA로 변환
            if santa_img.mode != 'RGBA':
                santa_img = santa_img.convert('RGBA')
            
            # 이미지 붙이기
            img.paste(santa_img, (paste_x, paste_y), santa_img)
            
        except Exception as e:
            # 이미지 로딩 실패시 흰색 원으로 대체
            circle_size = size * 0.35
            draw.ellipse([x - circle_size, y - circle_size, x + circle_size, y + circle_size], 
                         fill='white', outline='white')
        
        # 목적지 표시 (초록색 별 + 선물 상자 이미지)
        dest_pos = buildings[destination]
        dest_row, dest_col = dest_pos
        dest_x = int(dest_col * grid_width)
        dest_y = int(dest_row * grid_height - grid_height * 0.3)  # 교차점 위쪽에 표시
        
        star_size = size * 0.8
        # 별 모양 그리기 (배경)
        star_points = [
            (dest_x, dest_y - star_size),
            (dest_x + star_size * 0.3, dest_y - star_size * 0.3),
            (dest_x + star_size, dest_y),
            (dest_x + star_size * 0.3, dest_y + star_size * 0.3),
            (dest_x, dest_y + star_size),
            (dest_x - star_size * 0.3, dest_y + star_size * 0.3),
            (dest_x - star_size, dest_y),
            (dest_x - star_size * 0.3, dest_y - star_size * 0.3),
        ]
        draw.polygon(star_points, fill='lime', outline='green')
        
        # 선물 상자 이미지를 별 중앙에 추가
        try:
            # 선물 상자 이미지 로드 (상대 경로)
            gift_path = os.path.join(os.path.dirname(__file__), "gift box.jpeg")
            gift_img = Image.open(gift_path)
            
            # 이미지 크기 조정
            gift_size = int(star_size * 0.9)
            gift_img = gift_img.resize((gift_size, gift_size), Image.Resampling.LANCZOS)
            
            # 이미지를 중앙에 붙이기 위한 위치 계산
            paste_x = int(dest_x - gift_size / 2)
            paste_y = int(dest_y - gift_size / 2)
            
            # 투명도 처리를 위해 RGBA로 변환
            if gift_img.mode != 'RGBA':
                gift_img = gift_img.convert('RGBA')
            
            # 이미지 붙이기
            img.paste(gift_img, (paste_x, paste_y), gift_img)
            
        except Exception as e:
            # 이미지 로딩 실패시 별만 표시
            pass
        
        return img
    except Exception as e:
        st.error(f"Error loading image: {e}")
        return None

# 타이틀
st.title(f"🗺️ Where is the {st.session_state.end}?")
st.markdown("### 🎅 Santa is very slow. Help Santa go to his place!")

# 게임 정보
col1, col2, col3 = st.columns(3)
with col1:
    st.info(f"📍 **Start:** {st.session_state.start}")
with col2:
    st.success(f"🎯 **Destination:** {st.session_state.end}")
with col3:
    st.warning(f"🧭 **Current Direction:** {direction_names[st.session_state.direction]}")

# 지도 표시 영역
st.write("---")

# 지도 이미지 경로 (상대 경로 사용)
import os
map_image_path = os.path.join(os.path.dirname(__file__), "map.png")

# 지도와 버튼을 나란히 배치 (지도 크기 축소)
map_col, button_col = st.columns([1.2, 1])

with map_col:
    # 지도 이미지에 차량 표시
    map_with_car = create_map_with_car(
        map_image_path, 
        st.session_state.current_pos, 
        st.session_state.direction,
        st.session_state.end
    )
    
    if map_with_car:
        st.image(map_with_car, use_container_width=True)
    
    # CSS로 지도 크기 조정
    st.markdown("""
    <style>
    [data-testid="stImage"] {
        max-height: 500px;
    }
    </style>
    """, unsafe_allow_html=True)

with button_col:

    # 컨트롤 버튼
    if not st.session_state.completed:
        st.subheader("🎮 Directions")
        
        if st.button("⬆️ Go Straight", use_container_width=True, key="go"):
            new_pos = move_forward(st.session_state.current_pos, st.session_state.direction)
            if new_pos != st.session_state.current_pos:
                st.session_state.current_pos = new_pos
                st.session_state.moves.append("Go straight")
                st.rerun()
        
        if st.button("↪️ Turn Right", use_container_width=True, key="right"):
            st.session_state.direction = get_new_direction(st.session_state.direction, "turn_right")
            st.session_state.moves.append("Turn right")
            st.rerun()
        
        if st.button("↩️ Turn Left", use_container_width=True, key="left"):
            st.session_state.direction = get_new_direction(st.session_state.direction, "turn_left")
            st.session_state.moves.append("Turn left")
            st.rerun()
        
        st.write("---")
        
        # 목적지 근처에 있을 때만 버튼 활성화
        near_destination = check_near_destination()
        
        if st.button("👈 It's on your left", use_container_width=True, key="dest_left", disabled=not near_destination):
            if not near_destination:
                st.session_state.message = "❌ You're too far! Get closer to the destination first."
                st.rerun()
            
            # 목적지 위치
            end_pos = buildings[st.session_state.end]
            current_pos = st.session_state.current_pos
            current_dir = st.session_state.direction
            
            # 목적지가 어느 방향에 있는지 계산
            row_diff = end_pos[0] - current_pos[0]
            
            # 목적지가 왼쪽에 있는지 판단
            is_on_left = False
            
            # 같은 위치인 경우: 진행 방향에 따라 판단
            if current_pos == end_pos:
                # 동쪽(1) 또는 남쪽(2)을 향하면 북쪽이 왼쪽
                if current_dir == 1 or current_dir == 2:
                    is_on_left = True
            else:
                # 다른 위치: 목적지가 남쪽에 있으면 왼쪽
                is_on_left = (row_diff > 0)
            
            if is_on_left:
                st.session_state.completed = True
                st.session_state.message = f"🎉 Perfect! The {st.session_state.end} is on your left!"
                st.session_state.moves.append("It's on your left ✓")
            else:
                st.session_state.message = "❌ No, it's not on your left. Try again!"
                st.session_state.moves.append("It's on your left ✗")
            st.rerun()
        
        if st.button("👉 It's on your right", use_container_width=True, key="dest_right", disabled=not near_destination):
            if not near_destination:
                st.session_state.message = "❌ You're too far! Get closer to the destination first."
                st.rerun()
            
            # 목적지 위치
            end_pos = buildings[st.session_state.end]
            current_pos = st.session_state.current_pos
            current_dir = st.session_state.direction
            
            # 목적지가 어느 방향에 있는지 계산
            row_diff = end_pos[0] - current_pos[0]
            
            # 목적지가 오른쪽에 있는지 판단
            is_on_right = False
            
            # 같은 위치인 경우: 진행 방향에 따라 판단
            if current_pos == end_pos:
                # 서쪽(3) 또는 북쪽(0)을 향하면 북쪽이 오른쪽
                if current_dir == 3 or current_dir == 0:
                    is_on_right = True
            else:
                # 다른 위치: 목적지가 북쪽에 있으면 오른쪽
                is_on_right = (row_diff < 0)
            
            if is_on_right:
                st.session_state.completed = True
                st.session_state.message = f"🎉 Perfect! The {st.session_state.end} is on your right!"
                st.session_state.moves.append("It's on your right ✓")
            else:
                st.session_state.message = "❌ No, it's not on your right. Try again!"
                st.session_state.moves.append("It's on your right ✗")
            st.rerun()
        
        # 이동 기록을 버튼 아래에 표시
        if st.session_state.moves:
            st.write("---")
            st.subheader("📝 Your moves:")
            # 행간 간격을 줄인 스타일 적용
            moves_html = "<div style='line-height: 1.3;'>"
            for i, move in enumerate(st.session_state.moves, 1):
                moves_html += f"<p style='margin: 2px 0;'>{i}. {move}</p>"
            moves_html += "</div>"
            st.markdown(moves_html, unsafe_allow_html=True)
    else:
        # 축하 효과 (풍선 2번)
        st.balloons()
        import time
        time.sleep(0.5)
        st.balloons()
        
        # 큰 축하 메시지
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <h1 style='color: gold; font-size: 3em; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
                🎊 CONGRATULATIONS! 🎊
            </h1>
            <h2 style='color: #4CAF50; font-size: 2em;'>
                🎉 You Found the {st.session_state.end}! 🎉
            </h2>
            <p style='font-size: 1.5em; color: #FF6B6B;'>
                🎁 Great Job! 🎁
            </p>
        </div>
        """.format(st=st), unsafe_allow_html=True)
        
        # 완료 후에도 이동 기록 표시
        if st.session_state.moves:
            st.write("---")
            st.subheader("📝 Your moves:")
            # 행간 간격을 줄인 스타일 적용
            moves_html = "<div style='line-height: 1.3;'>"
            for i, move in enumerate(st.session_state.moves, 1):
                moves_html += f"<p style='margin: 2px 0;'>{i}. {move}</p>"
            moves_html += "</div>"
            st.markdown(moves_html, unsafe_allow_html=True)

# 메시지 표시
if st.session_state.message:
    st.write("---")
    if st.session_state.completed:
        st.success(st.session_state.message)
    else:
        st.info(st.session_state.message)

# 새 게임 버튼
st.write("---")
if st.button("🔄 New Game", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
