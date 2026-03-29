#!/usr/bin/env python3
"""
Dota 2 Match Analyzer
Анализирует ваши матчи через OpenDota API
"""

import requests
import json
from datetime import datetime
from collections import defaultdict

BASE_URL = "https://api.opendota.com/api"


class DotaAnalyzer:
    def __init__(self, player_id):
        """
        Инициализация анализатора

        Args:
            player_id: Steam ID игрока (можно найти на https://www.opendota.com/)
        """
        self.player_id = player_id
        self.session = requests.Session()
        self.heroes = {}
        self._load_heroes()

    def _load_heroes(self):
        """Загрузить список героев"""
        resp = self.session.get(f"{BASE_URL}/heroes")
        if resp.status_code == 200:
            for hero in resp.json():
                self.heroes[hero["id"]] = {
                    "name": hero["localized_name"],
                    "primary_attr": hero.get("primary_attr"),
                    "attack_type": hero.get("attack_type"),
                    "roles": hero.get("roles", [])
                }
    
    def _guess_lane(self, hero_id, match):
        """Определить позицию по герою и статистике"""
        hero = self.heroes.get(hero_id, {})
        roles = hero.get("roles", [])
        last_hits = match.get("last_hits", 0)
        supports = {"Support", "Hard Support", "Soft Support", "Nuker", "Disabler"}
        
        # Пробуем по ролям
        if "Carry" in roles and "Support" not in roles:
            if last_hits > 200:
                return 1  # Pos 1
            elif last_hits > 100:
                return 2  # Pos 2
        if "Support" in roles or last_hits < 50:
            return 5 if last_hits < 30 else 4
        if "Offlaner" in roles or "Initiator" in roles or "Durable" in roles:
            return 3
        
        # По фарму
        if last_hits > 250:
            return 1
        elif last_hits > 150:
            return 2
        elif last_hits > 80:
            return 3
        elif last_hits > 40:
            return 4
        return 5
        
    def get_player_info(self):
        """Получить информацию об игроке"""
        print(f"\n🔍 Поиск игрока {self.player_id}...")
        resp = self.session.get(f"{BASE_URL}/players/{self.player_id}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Никнейм: {data.get('profile', {}).get('personaname', 'Unknown')}")
            
            # Рейтинг
            mmr = data.get('mmr') or data.get('solo_mmr')
            mmr_estimate = data.get('mmr_estimate', {}).get('estimate')
            rank_tier = data.get('rank_tier')
            leaderboard_rank = data.get('leaderboard_rank')
            
            if mmr:
                print(f"📊 MMR: {mmr}")
            elif mmr_estimate:
                print(f"📊 MMR (оценка): {mmr_estimate}")
            elif rank_tier:
                tier_names = {
                    1: "Herald", 2: "Guardian", 3: "Crusader",
                    4: "Archon", 5: "Legend", 6: "Ancient",
                    7: "Divine", 8: "Immortal"
                }
                tier = (rank_tier - 1) // 10
                division = (rank_tier - 1) % 10 + 1
                tier_name = tier_names.get(min(tier + 1, 8), "Unknown")
                print(f"📊 Ранг: {tier_name} {division}")
            else:
                print("📊 Рейтинг: N/A (скрыт или нет рейтинга)")
            
            if leaderboard_rank:
                print(f"🏆 Топ рейтинга: #{leaderboard_rank}")
            
            return data
        print("❌ Игрок не найден")
        return None
    
    def get_recent_matches(self, limit=20):
        print(f"\n📥 Загрузка последних матчей (макс. 20)...")
        resp = self.session.get(f"{BASE_URL}/players/{self.player_id}/recentMatches")
        if resp.status_code == 200:
            return resp.json()
        print("❌ Не удалось загрузить матчи")
        return []
    
    def analyze_matches(self, matches):
        """Анализ матчей"""
        if not matches:
            print("Нет матчей для анализа")
            return
        
        wins = 0
        losses = 0
        heroes_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "kda": []})
        roles_stats = defaultdict(lambda: {"wins": 0, "losses": 0})
        avg_kills = 0
        avg_deaths = 0
        avg_assists = 0
        total_gpm = 0
        total_xpm = 0
        
        for match in matches:
            player_slot = match.get("player_slot", 0)
            radiant_win = match.get("radiant_win", False)
            is_win = (player_slot < 128) == radiant_win
            
            if is_win:
                wins += 1
            else:
                losses += 1
            
            hero_id = match.get("hero_id", 0)
            hero_info = self.heroes.get(hero_id, {})
            hero_name = hero_info.get("name", f"Unknown (ID:{hero_id})") if isinstance(hero_info, dict) else hero_info
            kda = (match.get("kills", 0), match.get("deaths", 0), match.get("assists", 0))

            heroes_stats[hero_name]["kda"].append(kda)
            if is_win:
                heroes_stats[hero_name]["wins"] += 1
            else:
                heroes_stats[hero_name]["losses"] += 1

            lane = match.get("lane_role")
            if lane is None:
                lane = self._guess_lane(hero_id, match)
            if is_win:
                roles_stats[lane]["wins"] += 1
            else:
                roles_stats[lane]["losses"] += 1
            
            avg_kills += match.get("kills", 0)
            avg_deaths += match.get("deaths", 0)
            avg_assists += match.get("assists", 0)
            total_gpm += match.get("gold_per_min", 0)
            total_xpm += match.get("xp_per_min", 0)
        
        total_matches = len(matches)
        
        print("\n" + "="*50)
        print("📊 ОБЩАЯ СТАТИСТИКА")
        print("="*50)
        print(f"Матчей: {total_matches}")
        print(f"Побед: {wins} | Поражений: {losses}")
        print(f"Win Rate: {wins/total_matches*100:.1f}%")
        print(f"\nСредние показатели:")
        print(f"  K/D/A: {avg_kills/total_matches:.1f} / {avg_deaths/total_matches:.1f} / {avg_assists/total_matches:.1f}")
        print(f"  KDA Ratio: {(avg_kills+avg_assists)/max(avg_deaths,1)/total_matches:.2f}")
        print(f"  GPM: {total_gpm/total_matches:.0f}")
        print(f"  XPM: {total_xpm/total_matches:.0f}")
        
        # Лучшие герои
        print("\n" + "="*50)
        print("🦸 ЛУЧШИЕ ГЕРОИ (по винрейту, мин. 2 игры)")
        print("="*50)
        
        best_heroes = []
        for hero, stats in heroes_stats.items():
            total = stats["wins"] + stats["losses"]
            if total >= 2:
                wr = stats["wins"] / total * 100
                best_heroes.append((hero, stats["wins"], stats["losses"], wr))
        
        best_heroes.sort(key=lambda x: x[3], reverse=True)
        
        for i, (hero, w, l, wr) in enumerate(best_heroes[:5], 1):
            print(f"{i}. {hero}: {w}W/{l}L (WR: {wr:.1f}%)")
        
        # Худшие герои
        print("\n" + "="*50)
        print("⚠️ ХУДШИЕ ГЕРОИ (по винрейту, мин. 2 игры)")
        print("="*50)
        
        worst_heroes = sorted(best_heroes, key=lambda x: x[3])
        for i, (hero, w, l, wr) in enumerate(worst_heroes[:5], 1):
            print(f"{i}. {hero}: {w}W/{l}L (WR: {wr:.1f}%)")
        
        # Статистика по позициям
        print("\n" + "="*50)
        print("📍 СТАТИСТИКА ПО ПОЗИЦИЯМ")
        print("="*50)
        
        lane_names = {
            1: "Carry (Pos 1)",
            2: "Mid (Pos 2)",
            3: "Offlane (Pos 3)",
            4: "Soft Support (Pos 4)",
            5: "Hard Support (Pos 5)"
        }
        
        for lane, stats in sorted(roles_stats.items()):
            total = stats["wins"] + stats["losses"]
            if total > 0:
                lane_name = lane_names.get(lane, f"Pos {lane}")
                wr = stats["wins"] / total * 100
                print(f"{lane_name}: {stats['wins']}W/{stats['losses']}L (WR: {wr:.1f}%)")
        
        # Рекомендации
        print("\n" + "="*50)
        print("💡 РЕКОМЕНДАЦИИ")
        print("="*50)
        
        if best_heroes and best_heroes[0][0] != "Unknown":
            print(f"✅ Продолжайте играть на: {best_heroes[0][0]}")
        
        if avg_deaths / total_matches > 7:
            print("⚠️ Много смертей! Улучшите позиционку")
        
        if total_gpm / total_matches < 400:
            print("⚠️ Низкий GPM! Улучшите фарм")
        
        wr = wins / total_matches * 100
        if wr < 45:
            print("⚠️ Винрейт ниже 45% — сделайте перерыв или смените героев")
        elif wr > 55:
            print("🔥 Отличный винрейт! Продолжайте в том же духе!")
        
        print()
    
    def save_matches(self, matches, filename="matches.json"):
        """Сохранить матчи в JSON"""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        print(f"💾 Матчи сохранены в {filename}")


def main():
    print("="*50)
    print("🎮 DOTA 2 MATCH ANALYZER")
    print("="*50)
    
    # Запросить Steam ID
    player_id = input("\nВведите ваш Steam ID (или ID из OpenDota): ").strip()
    
    if not player_id:
        print("❌ ID не введён")
        return
    
    analyzer = DotaAnalyzer(player_id)
    
    # Информация об игроке
    player_info = analyzer.get_player_info()
    if not player_info:
        return
    
    # Загрузка и анализ матчей
    matches = analyzer.get_recent_matches(limit=50)
    
    if matches:
        analyzer.analyze_matches(matches)
        
        # Сохранение
        try:
            save = input("Сохранить матчи в JSON? (y/n): ").strip().lower()
            if save == "y":
                analyzer.save_matches(matches)
        except EOFError:
            pass  # Автотесты без интерактива
    
    print("\n👋 Удачи в катках, сэр!")


if __name__ == "__main__":
    main()
