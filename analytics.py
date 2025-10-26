from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from db_operations import DatabaseOperations
from database import User, Profit
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import pandas as pd


class AdvancedAnalytics:
    
    @staticmethod
    async def get_smart_analytics(mini_head_id: Optional[int] = None) -> Dict:
        """Получить умную аналитику для команды или глобально"""
        
        if mini_head_id:
            # Аналитика для команды Mini Head
            team = await DatabaseOperations.get_mini_head_team(mini_head_id)
            team_ids = [member.id for member in team]
            
            if not team_ids:
                return {
                    'avg_profit': 0,
                    'growth_week': 0,
                    'active_members': 0,
                    'total_members': 0,
                    'productivity': 0,
                    'avg_check': 0
                }
            
            # Статистика за текущую неделю
            week_stats = await DatabaseOperations.get_team_statistics(mini_head_id, 'week')
            # Статистика за прошлую неделю
            prev_week_start = datetime.utcnow() - timedelta(days=14)
            prev_week_end = datetime.utcnow() - timedelta(days=7)
            
            # Рост за неделю
            prev_week_profit = 0  # TODO: реализовать получение за прошлую неделю
            current_week_profit = week_stats['total']
            
            if prev_week_profit > 0:
                growth = ((current_week_profit - prev_week_profit) / prev_week_profit) * 100
            else:
                growth = 100 if current_week_profit > 0 else 0
            
            # Средний профит на участника
            avg_profit = current_week_profit / len(team_ids) if team_ids else 0
            
            # Активные участники (те, кто получил профит за неделю)
            active_count = 0
            for member_id in team_ids:
                member_stats = await DatabaseOperations.get_user_statistics(member_id)
                if member_stats['week'] > 0:
                    active_count += 1
            
            # Продуктивность (активные / всего)
            productivity = active_count / len(team_ids) if team_ids else 0
            
            # Средний чек профита
            avg_check = week_stats['total'] / week_stats['count'] if week_stats['count'] > 0 else 0
            
            return {
                'avg_profit': avg_profit,
                'growth_week': growth,
                'active_members': active_count,
                'total_members': len(team_ids),
                'productivity': productivity,
                'avg_check': avg_check,
                'total_profit': current_week_profit
            }
        
        else:
            # Глобальная аналитика
            all_users = await DatabaseOperations.get_all_users()
            global_stats = await DatabaseOperations.get_global_statistics('week')
            
            # Средний профит на участника
            avg_profit = global_stats['total'] / len(all_users) if all_users else 0
            
            # Активные участники
            active_count = global_stats['active_users']
            
            # Продуктивность
            productivity = active_count / len(all_users) if all_users else 0
            
            # Средний чек
            avg_check = global_stats['total'] / global_stats['count'] if global_stats['count'] > 0 else 0
            
            return {
                'avg_profit': avg_profit,
                'growth_week': 0,  # TODO: рассчитать рост
                'active_members': active_count,
                'total_members': len(all_users),
                'productivity': productivity,
                'avg_check': avg_check,
                'total_profit': global_stats['total']
            }
    
    @staticmethod
    async def get_live_dashboard() -> Dict:
        """Получить данные для live dashboard"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Статистика за сегодня
        today_stats = await DatabaseOperations.get_global_statistics('day')
        
        # Количество Mini Heads
        mini_heads = await DatabaseOperations.get_all_users(role='Mini Head')
        
        # Всего воркеров
        workers = await DatabaseOperations.get_all_users(role='Worker')
        
        # Средний профит
        avg_profit = today_stats['total'] / today_stats['active_users'] if today_stats['active_users'] > 0 else 0
        
        # Самый активный сегодня
        top_today = await DatabaseOperations.get_top_users(limit=1)
        most_active = None
        if top_today:
            most_active = {
                'username': top_today[0][0].username,
                'profit': top_today[0][1]
            }
        
        return {
            'total_today': today_stats['total'],
            'mini_heads_count': len(mini_heads),
            'workers_count': len(workers),
            'avg_profit': avg_profit,
            'most_active': most_active,
            'active_users': today_stats['active_users']
        }
    
    @staticmethod
    async def check_inactive_users(days: int = 3) -> List[Tuple[User, User, int]]:
        """Проверить неактивных пользователей"""
        all_users = await DatabaseOperations.get_all_users()
        inactive = []
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        for user in all_users:
            if user.role == 'Worker':
                # Получаем последний профит
                profits = await DatabaseOperations.get_user_profits(user.id, limit=1)
                
                if not profits or profits[0].created_at < cutoff_date:
                    # Пользователь неактивен
                    days_inactive = (datetime.utcnow() - profits[0].created_at).days if profits else 999
                    
                    # Получаем наставника
                    mentor = None
                    if user.mini_head_id:
                        mentor = await DatabaseOperations.get_user_by_id(user.mini_head_id)
                    
                    inactive.append((user, mentor, days_inactive))
        
        return inactive
    
    @staticmethod
    async def generate_profit_chart(user_id: Optional[int] = None, period_days: int = 30) -> BytesIO:
        """Генерирует график профитов"""
        plt.figure(figsize=(12, 6))
        plt.style.use('seaborn-v0_8-darkgrid')
        
        if user_id:
            # График для конкретного пользователя
            profits = await DatabaseOperations.get_user_profits(user_id, limit=1000)
            
            # Группируем по дням
            df = pd.DataFrame([{
                'date': p.created_at.date(),
                'amount': p.amount
            } for p in profits])
            
            if not df.empty:
                daily = df.groupby('date')['amount'].sum().reset_index()
                daily = daily.sort_values('date')
                
                plt.plot(daily['date'], daily['amount'], marker='o', linewidth=2, markersize=6)
                plt.title('График профитов', fontsize=16, fontweight='bold')
                plt.xlabel('Дата', fontsize=12)
                plt.ylabel('Профит (₽)', fontsize=12)
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
        
        else:
            # Глобальный график
            # TODO: реализовать глобальный график
            pass
        
        # Сохраняем в BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    async def generate_team_comparison_chart() -> BytesIO:
        """Генерирует график сравнения команд Mini Heads"""
        plt.figure(figsize=(12, 6))
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # Получаем всех Mini Heads
        mini_heads = await DatabaseOperations.get_all_users(role='Mini Head')
        
        names = []
        profits = []
        
        for mh in mini_heads:
            stats = await DatabaseOperations.get_team_statistics(mh.id, 'month')
            names.append(mh.username or f"ID{mh.telegram_id}")
            profits.append(stats['total'])
        
        if names:
            plt.bar(names, profits, color='#4CAF50', alpha=0.8)
            plt.title('Сравнение команд Mini Heads (месяц)', fontsize=16, fontweight='bold')
            plt.xlabel('Mini Head', fontsize=12)
            plt.ylabel('Профит команды (₽)', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            plt.grid(True, alpha=0.3, axis='y')
            plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        
        return buf
    
    @staticmethod
    async def get_heads_stats() -> List[Dict]:
        """Получить статистику по всем Mini Heads"""
        mini_heads = await DatabaseOperations.get_all_users(role='Mini Head')
        
        stats_list = []
        for mh in mini_heads:
            team_stats = await DatabaseOperations.get_team_statistics(mh.id, 'week')
            team = await DatabaseOperations.get_mini_head_team(mh.id)
            
            # Рост за неделю (упрощенно)
            month_stats = await DatabaseOperations.get_team_statistics(mh.id, 'month')
            growth = 0  # TODO: рассчитать реальный рост
            
            stats_list.append({
                'username': mh.username or f"ID{mh.telegram_id}",
                'profit': team_stats['total'],
                'members': len(team),
                'growth': growth
            })
        
        # Сортируем по профиту
        stats_list.sort(key=lambda x: x['profit'], reverse=True)
        
        return stats_list
    
    @staticmethod
    def format_analytics_message(analytics: Dict, team_name: str = "Команда") -> str:
        """Форматирует сообщение с аналитикой"""
        text = f"📊 Аналитика {team_name}\n\n"
        
        text += f"💸 Средний профит участника: {int(analytics['avg_profit']):,} ₽\n"
        
        # Рост
        growth = analytics['growth_week']
        growth_emoji = "📈" if growth > 0 else "📉" if growth < 0 else "➡️"
        text += f"{growth_emoji} Рост за неделю: {growth:+.1f}%\n"
        
        text += f"👥 Активных работников: {analytics['active_members']} / {analytics['total_members']}\n"
        
        # Продуктивность
        productivity = analytics['productivity']
        prod_emoji = "🔥" if productivity > 0.8 else "⚡" if productivity > 0.5 else "⚠️"
        text += f"{prod_emoji} Продуктивность: {productivity:.2f}\n"
        
        text += f"💰 Средний чек: {int(analytics['avg_check']):,} ₽\n"
        text += f"💸 Общий профит: {int(analytics['total_profit']):,} ₽"
        
        return text
    
    @staticmethod
    def format_live_dashboard(dashboard: Dict) -> str:
        """Форматирует live dashboard"""
        text = "📊 LIVE DASHBOARD\n"
        text += f"🕐 Обновлено: {datetime.now().strftime('%H:%M')}\n\n"
        
        text += f"💰 Общий профит сегодня: {int(dashboard['total_today']):,} ₽\n"
        text += f"👥 Активных Mini Head'ов: {dashboard['mini_heads_count']}\n"
        text += f"🧑‍💻 Всего воркеров: {dashboard['workers_count']}\n"
        text += f"💹 Средний профит: {int(dashboard['avg_profit']):,} ₽\n"
        
        if dashboard['most_active']:
            text += f"⚡ Самый активный: @{dashboard['most_active']['username']} "
            text += f"({int(dashboard['most_active']['profit']):,} ₽)\n"
        
        text += f"\n👤 Активных пользователей: {dashboard['active_users']}"
        
        return text
