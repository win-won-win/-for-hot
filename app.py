import streamlit as st
import pandas as pd
import io
from datetime import datetime, time
import base64

# ページ設定
st.set_page_config(
    page_title="日勤夜勤給与計算ツール",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS（ダークモード）
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
        color: #ffffff;
    }
    
    .main-header {
        text-align: center;
        color: #4CAF50;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    .section-header {
        color: #81C784;
        font-size: 1.5rem;
        font-weight: bold;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #4CAF50;
        padding-bottom: 0.5rem;
    }
    
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
    }
    
    .stDataFrame {
        background-color: #2d2d2d;
    }
    
    .calculation-result {
        background-color: #2d2d2d;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    
    .employee-card {
        background-color: #2d2d2d;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border: 1px solid #4CAF50;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    
    .metric-container {
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .metric-item {
        background-color: #333333;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        min-width: 150px;
        border: 1px solid #555555;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
        color: #4CAF50;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #cccccc;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def create_initial_csv_template():
    """初期CSVテンプレートを作成"""
    template_data = {
        '日付': ['2024-01-15', '2024-01-15'],
        '日勤 or 夜勤': ['日勤', '夜勤'],
        '従業員名': ['山田 太郎', '佐藤 花子'],
        '処遇改善加算％': [18, 15],
        '勤務開始時間': ['09:00', '18:00'],
        '勤務終了時間': ['18:00', '32:29'],
        '休憩時間': [1.0, 1.0],
        '基本給': ['', ''],
        '夜勤手当': ['', ''],
        '深夜手当': ['', ''],
        '残業手当': ['', ''],
        '処遇改善加算手当': ['', ''],
        '日当': ['', '']
    }
    return pd.DataFrame(template_data)

def parse_time(time_str):
    """時間文字列を解析して時間数を返す（24時間を超える場合も対応）"""
    try:
        # 文字列から余分な文字を削除
        time_str = str(time_str).strip()
        
        if ':' in time_str:
            # 時:分:秒 または 時:分 の形式に対応
            time_parts = time_str.split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1]) if len(time_parts) > 1 else 0
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0
            
            # 時間数に変換（秒も考慮）
            return hours + minutes / 60 + seconds / 3600
        else:
            return float(time_str)
    except Exception as e:
        print(f"時間解析エラー: {time_str} - {e}")
        return 0

def calculate_work_hours(start_time, end_time, break_time=0):
    """勤務時間を計算（休憩時間を考慮）"""
    start_hours = parse_time(start_time)
    end_hours = parse_time(end_time)
    
    # 翌日にまたがる場合の処理
    if end_hours < start_hours:
        end_hours += 24
    
    # 総勤務時間から休憩時間を引く
    total_hours = end_hours - start_hours
    actual_work_hours = total_hours - float(break_time)
    
    return max(0, actual_work_hours)  # 負の値にならないように

def calculate_salary(row):
    """給与計算メイン関数"""
    work_type = row['日勤 or 夜勤']
    break_time = row.get('休憩時間', 0)
    work_hours = calculate_work_hours(row['勤務開始時間'], row['勤務終了時間'], break_time)
    improvement_rate = row['処遇改善加算％'] / 100
    
    if work_type == '日勤':
        # 日勤の計算
        basic_salary = work_hours * 1300
        improvement_allowance = work_hours * 1200 * improvement_rate
        night_allowance = 0
        midnight_allowance = 0
        overtime_allowance = 0
        
    else:  # 夜勤
        # 夜勤の計算
        basic_salary = work_hours * 1200
        night_allowance = 3000
        midnight_allowance = 1800
        overtime_hours = max(0, work_hours - 8)
        overtime_allowance = overtime_hours * 1200 * 0.25
        improvement_allowance = work_hours * 1200 * improvement_rate
    
    daily_total = basic_salary + night_allowance + midnight_allowance + overtime_allowance + improvement_allowance
    
    return {
        '基本給': int(basic_salary),
        '夜勤手当': int(night_allowance),
        '深夜手当': int(midnight_allowance),
        '残業手当': int(overtime_allowance),
        '処遇改善加算手当': int(improvement_allowance),
        '日当': int(daily_total),
        '勤務時間': round(work_hours, 1),
        '休憩時間': round(float(break_time), 1)
    }

def format_currency(amount):
    """金額をフォーマット"""
    return f"¥{amount:,}"

def create_download_link(df, filename):
    """CSVダウンロードリンクを作成"""
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
    href = f'<a href="data:text/csv;base64,{b64}" download="{filename}" style="color: #4CAF50; text-decoration: none; font-weight: bold;">📥 {filename} をダウンロード</a>'
    return href

def main():
    # メインヘッダー
    st.markdown('<h1 class="main-header">💰 日勤夜勤給与計算ツール</h1>', unsafe_allow_html=True)
    
    # セクション1: 初期CSVテンプレートダウンロード
    st.markdown('<div class="section-header">📋 初期CSVテンプレート</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📥 初期CSVテンプレートをダウンロード", key="template_download"):
            template_df = create_initial_csv_template()
            st.markdown(create_download_link(template_df, "給与計算テンプレート.csv"), unsafe_allow_html=True)
            st.success("✅ テンプレートが生成されました！上のリンクからダウンロードしてください。")
    
    # セクション2: CSVアップロード
    st.markdown('<div class="section-header">📤 勤怠CSVアップロード</div>', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader(
        "勤怠データが入力されたCSVファイルをアップロードしてください",
        type=['csv'],
        help="初期テンプレートに勤怠データを入力したCSVファイルをアップロードしてください"
    )
    
    if uploaded_file is not None:
        try:
            # CSVファイルを読み込み
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            
            st.success("✅ CSVファイルが正常にアップロードされました！")
            
            # アップロードされたデータを表示
            st.markdown('<div class="section-header">📊 アップロードされたデータ</div>', unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True)
            
            # 計算実行
            if st.button("🧮 給与計算を実行", key="calculate"):
                results = []
                
                for index, row in df.iterrows():
                    calculation = calculate_salary(row)
                    result_row = row.copy()
                    result_row.update(calculation)
                    results.append(result_row)
                
                results_df = pd.DataFrame(results)
                
                # 計算結果を表示
                st.markdown('<div class="section-header">💰 計算結果</div>', unsafe_allow_html=True)
                
                # 各従業員の詳細表示
                for index, row in results_df.iterrows():
                    with st.container():
                        st.markdown(f'<div class="employee-card">', unsafe_allow_html=True)
                        
                        # 従業員情報ヘッダー（日付を含む）
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        with col1:
                            st.markdown(f"**👤 {row['従業員名']}**")
                        with col2:
                            work_date = row.get('日付', '日付不明')
                            st.markdown(f"**📅 {work_date}**")
                        with col3:
                            st.markdown(f"**{row['日勤 or 夜勤']}**")
                        with col4:
                            work_hours = row.get('勤務時間', calculate_work_hours(row['勤務開始時間'], row['勤務終了時間'], row.get('休憩時間', 0)))
                            st.markdown(f"**実働時間: {work_hours:.1f}時間**")
                        
                        # 勤務時間詳細
                        break_time = row.get('休憩時間', 0)
                        total_time = calculate_work_hours(row['勤務開始時間'], row['勤務終了時間'], 0)  # 休憩時間を引かない総時間
                        work_date = row.get('日付', '日付不明')
                        st.markdown(f"📅 **勤務日:** {work_date}")
                        st.markdown(f"🕐 **勤務時間:** {row['勤務開始時間']} ～ {row['勤務終了時間']} (総時間: {total_time:.1f}時間, 休憩: {break_time:.1f}時間, 実働: {work_hours:.1f}時間)")
                        
                        # 計算式表示
                        work_hours = row.get('勤務時間', calculate_work_hours(row['勤務開始時間'], row['勤務終了時間'], row.get('休憩時間', 0)))
                        if row['日勤 or 夜勤'] == '日勤':
                            st.markdown(f"""
                            **📊 計算詳細:**
                            - 基本給: {work_hours:.1f}時間 × ¥1,300 = {format_currency(row['基本給'])}
                            - 処遇改善加算手当: {work_hours:.1f}時間 × ¥1,200 × {row['処遇改善加算％']}% = {format_currency(row['処遇改善加算手当'])}
                            """)
                        else:
                            overtime_hours = max(0, work_hours - 8)
                            st.markdown(f"""
                            **📊 計算詳細:**
                            - 基本給: {work_hours:.1f}時間 × ¥1,200 = {format_currency(row['基本給'])}
                            - 夜勤手当: 固定 = {format_currency(row['夜勤手当'])}
                            - 深夜手当: 固定 = {format_currency(row['深夜手当'])}
                            - 残業手当: {overtime_hours:.1f}時間 × ¥1,200 × 25% = {format_currency(row['残業手当'])}
                            - 処遇改善加算手当: {work_hours:.1f}時間 × ¥1,200 × {row['処遇改善加算％']}% = {format_currency(row['処遇改善加算手当'])}
                            """)
                        
                        # 手当詳細をメトリクス形式で表示
                        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
                        
                        metrics = [
                            ("基本給", row['基本給']),
                            ("夜勤手当", row['夜勤手当']),
                            ("深夜手当", row['深夜手当']),
                            ("残業手当", row['残業手当']),
                            ("処遇改善手当", row['処遇改善加算手当']),
                            ("日当合計", row['日当'])
                        ]
                        
                        cols = st.columns(len(metrics))
                        for i, (label, value) in enumerate(metrics):
                            if value > 0:  # 0円の項目は表示しない（日勤の場合の夜勤手当など）
                                with cols[i]:
                                    st.metric(label, format_currency(value))
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown("---")
                
                # 計算結果テーブル
                st.markdown('<div class="section-header">📋 計算結果一覧</div>', unsafe_allow_html=True)
                
                # 表示用にフォーマット
                display_df = results_df.copy()
                for col in ['基本給', '夜勤手当', '深夜手当', '残業手当', '処遇改善加算手当', '日当']:
                    display_df[col] = display_df[col].apply(format_currency)
                
                st.dataframe(display_df, use_container_width=True)
                
                # 合計金額表示
                total_amount = results_df['日当'].sum()
                st.markdown(f"""
                <div class="calculation-result">
                    <h3 style="color: #4CAF50; text-align: center;">💰 総支給額: {format_currency(total_amount)}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # 人事集計セクション（従業員ごと）
                st.markdown('<div class="section-header">📊 従業員別集計</div>', unsafe_allow_html=True)
                
                # 従業員ごとの集計（日付も含めてグループ化）
                group_columns = ['日付', '従業員名', '日勤 or 夜勤', '勤務開始時間', '勤務終了時間']
                employee_groups = results_df.groupby(group_columns).first().reset_index()
                
                # 従業員リストを作成（重複除去）
                unique_employees = employee_groups['従業員名'].unique().tolist()
                total_records = len(employee_groups)
                st.markdown(f"**📋 従業員リスト:** {', '.join(unique_employees)} (計{len(unique_employees)}名)")
                st.markdown(f"**📊 勤務記録:** 総{total_records}件の勤務記録")
                
                # 従業員ごとにまとめて表示
                for employee_name in unique_employees:
                    # 該当従業員の全勤務データを取得
                    employee_records = employee_groups[employee_groups['従業員名'] == employee_name].sort_values('日付')
                    
                    with st.container():
                        st.markdown(f'<div class="employee-card">', unsafe_allow_html=True)
                        
                        # 従業員名ヘッダー
                        st.markdown(f"### 👤 {employee_name}")
                        st.markdown("**📊 勤務データ一覧:**")
                        
                        # 勤務データを表形式で表示
                        work_data = []
                        total_work_hours = 0
                        total_salary = 0
                        
                        for _, record in employee_records.iterrows():
                            # 実働時間を計算
                            break_time = record.get('休憩時間', 0)
                            actual_work_hours = calculate_work_hours(
                                record['勤務開始時間'],
                                record['勤務終了時間'],
                                break_time
                            )
                            
                            work_data.append({
                                '日付': record['日付'],
                                '勤務形態': record['日勤 or 夜勤'],
                                '勤務時間': f"{record['勤務開始時間']}～{record['勤務終了時間']}",
                                '実働時間': f"{actual_work_hours:.1f}h",
                                '休憩時間': f"{break_time:.1f}h",
                                '日当': format_currency(record['日当'])
                            })
                            
                            total_work_hours += actual_work_hours
                            total_salary += record['日当']
                        
                        # データフレームとして表示
                        work_df = pd.DataFrame(work_data)
                        st.dataframe(work_df, use_container_width=True, hide_index=True)
                        
                        # 合計情報を表示
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("総勤務日数", f"{len(employee_records)}日")
                        with col2:
                            st.metric("総実働時間", f"{total_work_hours:.1f}時間")
                        with col3:
                            st.metric("総支給額", format_currency(total_salary))
                        
                        # 詳細な手当内訳（最新の勤務データから）
                        latest_record = employee_records.iloc[-1]
                        st.markdown("**💰 手当詳細（最新勤務日）:**")
                        allowance_cols = st.columns(5)
                        
                        allowances = [
                            ("基本給", latest_record['基本給']),
                            ("夜勤手当", latest_record['夜勤手当']),
                            ("深夜手当", latest_record['深夜手当']),
                            ("残業手当", latest_record['残業手当']),
                            ("処遇改善手当", latest_record['処遇改善加算手当'])
                        ]
                        
                        for i, (label, amount) in enumerate(allowances):
                            if amount > 0:  # 0円の項目は表示しない
                                with allowance_cols[i]:
                                    st.metric(label, format_currency(amount))
                        
                        st.markdown('</div>', unsafe_allow_html=True)
                        st.markdown("---")
                
                # 全体集計
                st.markdown('<div class="section-header">📊 全体集計</div>', unsafe_allow_html=True)
                
                # 重複除去したデータで集計
                unique_results = employee_groups
                
                # 集計データの計算
                total_employees = len(unique_results)
                day_shift_count = len(unique_results[unique_results['日勤 or 夜勤'] == '日勤'])
                night_shift_count = len(unique_results[unique_results['日勤 or 夜勤'] == '夜勤'])
                
                # 各手当の合計
                total_basic = unique_results['基本給'].sum()
                total_night = unique_results['夜勤手当'].sum()
                total_midnight = unique_results['深夜手当'].sum()
                total_overtime = unique_results['残業手当'].sum()
                total_improvement = unique_results['処遇改善加算手当'].sum()
                
                # 勤務時間の集計（正しく計算）
                total_work_hours = 0
                total_break_hours = 0
                for index, row in unique_results.iterrows():
                    work_hours = row.get('勤務時間', 0)
                    break_hours = row.get('休憩時間', 0)
                    total_work_hours += work_hours
                    total_break_hours += break_hours
                
                # 集計表示
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    <div class="employee-card">
                        <h4 style="color: #4CAF50; text-align: center;">👥 勤務形態別</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    st.metric("総従業員数", f"{total_employees}名")
                    st.metric("日勤", f"{day_shift_count}名")
                    st.metric("夜勤", f"{night_shift_count}名")
                    st.metric("総実働時間", f"{total_work_hours:.1f}時間")
                    st.metric("総休憩時間", f"{total_break_hours:.1f}時間")
                
                with col2:
                    st.markdown("""
                    <div class="employee-card">
                        <h4 style="color: #4CAF50; text-align: center;">💰 手当別合計</h4>
                    </div>
                    """, unsafe_allow_html=True)
                    st.metric("基本給合計", format_currency(total_basic))
                    st.metric("夜勤手当合計", format_currency(total_night))
                    st.metric("深夜手当合計", format_currency(total_midnight))
                    st.metric("残業手当合計", format_currency(total_overtime))
                    st.metric("処遇改善手当合計", format_currency(total_improvement))
                
                # ダウンロードボタン
                st.markdown('<div class="section-header">📥 計算結果ダウンロード</div>', unsafe_allow_html=True)
                
                # CSVダウンロードリンクを常に表示
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"給与計算結果_{timestamp}.csv"
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown(create_download_link(results_df, filename), unsafe_allow_html=True)
                    st.info("💡 上のリンクをクリックして計算結果CSVをダウンロードしてください。")
                
        except Exception as e:
            st.error(f"❌ CSVファイルの処理中にエラーが発生しました: {str(e)}")
            st.info("💡 CSVファイルの形式を確認してください。初期テンプレートと同じ列構成である必要があります。")

if __name__ == "__main__":
    main()