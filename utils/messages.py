"""
messages.py — Template pesan Telegram.
Semua pesan menggunakan ParseMode.MARKDOWN (v1).
Karakter spesial yang perlu di-escape di Markdown v1: * _ ` [
"""
from typing import Optional
import config
from game.player import Player
from game.rules import get_chain_suffix


def msg_welcome() -> str:
    return (
        "🎮 *Selamat datang di Bot Sambung Kata KBBI!*\n\n"
        "📖 Game seru untuk grup — sambung kata berdasarkan kamus KBBI Indonesia.\n\n"
        "📌 *Cara Bermain:*\n"
        "1️⃣ Undang bot ke grup\n"
        "2️⃣ Ketik /join untuk mendaftar\n"
        "3️⃣ Setelah min. 2 pemain join, ketik /mulai\n"
        "4️⃣ Sambung kata! Huruf awal = huruf terakhir kata sebelumnya\n\n"
        "Ketik /help untuk daftar perintah lengkap."
    )


def msg_help() -> str:
    return (
        "📋 *Daftar Perintah Bot Sambung Kata*\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🎮 *Game*\n"
        "/join — Daftar sebagai pemain\n"
        "/mulai — Mulai permainan (min. 2 pemain)\n"
        "/stop — Hentikan permainan\n"
        "/skip — Lewati giliran kamu (penalti -5 poin)\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📊 *Info & Statistik*\n"
        "/skor — Skor pemain sesi ini\n"
        "/info — Info game yang sedang berjalan\n"
        "/leaderboard — Ranking all-time grup ini\n"
        "/stats — Statistik pribadimu\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ *Admin*\n"
        "/resetgame — Reset game (admin grup)\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "📖 *Aturan:*\n"
        "• Kata harus ada di kamus KBBI\n"
        "• Min. 3 huruf\n"
        "• Huruf pertama = huruf terakhir kata sebelumnya\n"
        "• Kata tidak boleh diulang\n"
        "• Skip 3x = eliminated 💀\n"
        "• Timer 60 detik per giliran ⏱"
    )


def msg_group_only() -> str:
    return (
        "⛔ *Bot ini hanya bisa digunakan di grup Telegram!*\n\n"
        "Silakan undang bot ke grup kamu terlebih dahulu, "
        "lalu gunakan perintah di sana."
    )


def msg_joined(display_name: str, count: int) -> str:
    return (
        f"✅ {display_name} telah bergabung!\n"
        f"👥 Total pemain: *{count}*\n\n"
        f"Tunggu pemain lain join, lalu ketik /mulai untuk memulai."
    )


def msg_already_joined() -> str:
    return "ℹ️ Kamu sudah terdaftar sebagai pemain."


def msg_game_running_cannot_join() -> str:
    return "⚠️ Game sedang berjalan. Tunggu game selesai untuk join berikutnya."


def msg_game_started(
    players: list[Player],
    first_player: Player,
    starter_word: str,
) -> str:
    player_list = "\n".join(
        f"  {i+1}. {p.display_name}" for i, p in enumerate(players)
    )
    suffix = get_chain_suffix(starter_word)
    n = config.CHAIN_LETTERS
    label = f"{n} huruf" if n > 1 else "huruf"
    return (
        f"🚀 *Permainan dimulai!*\n\n"
        f"👥 *Pemain ({len(players)}):*\n{player_list}\n\n"
        f"📝 *Kata awal:* `{starter_word}`\n"
        f"🔤 Sambung dengan {label}: *{suffix.upper()}*\n\n"
        f"🎯 Giliran pertama: {first_player.display_name}\n"
        f"⏱ Waktu per giliran: {config.TURN_TIMEOUT_SECONDS} detik"
    )


def msg_your_turn(player: Player, last_word: str) -> str:
    suffix = get_chain_suffix(last_word)
    n = config.CHAIN_LETTERS
    label = f"{n} huruf" if n > 1 else "huruf"
    return (
        f"🎯 Giliran {player.display_name}! {player.lives_display}\n"
        f"📝 Kata terakhir: *{last_word}*\n"
        f"🔤 Awali dengan {label}: *{suffix.upper()}*\n"
        f"⏱ Waktu: {config.TURN_TIMEOUT_SECONDS} detik"
    )


def msg_word_accepted(word: str, points: int, bonus: int, next_player: Player) -> str:
    total = points + bonus
    bonus_str = f" (+{bonus} bonus kata panjang)" if bonus else ""
    suffix = get_chain_suffix(word)
    n = config.CHAIN_LETTERS
    label = f"{n} huruf" if n > 1 else "huruf"
    return (
        f"✅ *{word}* diterima! +{points}{bonus_str} = *+{total} poin*\n\n"
        f"🎯 Giliran selanjutnya: {next_player.display_name}\n"
        f"🔤 Awali dengan {label}: *{suffix.upper()}*\n"
        f"⏱ {config.TURN_TIMEOUT_SECONDS} detik..."
    )


def msg_scoreboard(players: list[Player], title: str = "📊 Skor Sesi Ini") -> str:
    lines = [f"*{title}*\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, p in enumerate(players):
        medal = medals[i] if i < 3 else f"{i+1}."
        elim = " (💀 Eliminated)" if p.is_eliminated else ""
        lines.append(
            f"{medal} {p.display_name}{elim}\n"
            f"   Poin: *{p.score}* | Kata: {p.words_submitted} | "
            f"Skip: {p.skip_count} | Nyawa: {p.lives_display}"
        )
    return "\n".join(lines)


def msg_game_info(
    last_word: str,
    current_player: Optional[Player],
    round_num: int,
    used_count: int,
) -> str:
    cp_str = current_player.display_name if current_player else "—"
    suffix = get_chain_suffix(last_word) if last_word else "—"
    n = config.CHAIN_LETTERS
    label = f"{n} huruf" if n > 1 else "huruf"
    return (
        f"ℹ️ *Info Game Saat Ini*\n\n"
        f"📝 Kata terakhir: *{last_word}*\n"
        f"🔤 Awali dengan {label}: *{suffix.upper()}*\n"
        f"🎯 Giliran: {cp_str}\n"
        f"🔢 Ronde: {round_num}\n"
        f"📚 Kata terpakai: {used_count}"
    )


def msg_game_over(winner: Optional[Player], players: list[Player]) -> str:
    if winner:
        win_str = f"🏆 *Pemenang: {winner.display_name}* dengan *{winner.score} poin*!"
    else:
        win_str = "🏁 Game berakhir tanpa pemenang."

    board = msg_scoreboard(players, "📊 Hasil Akhir")
    return f"🎊 *Game Selesai!*\n\n{win_str}\n\n{board}"


def msg_not_your_turn(current_player: Player) -> str:
    return f"⏳ Bukan giliran kamu! Sekarang giliran {current_player.display_name}."


def msg_no_game() -> str:
    return "❌ Tidak ada game yang berjalan. Ketik /join untuk memulai."


def msg_need_more_players(min_players: int) -> str:
    return (
        f"⚠️ Butuh minimal *{min_players} pemain* untuk mulai.\n"
        f"Minta teman-teman untuk ketik /join!"
    )
