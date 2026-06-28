ACCESS_DENIED = "Maaf, kamu tidak punya akses untuk menjalankan perintah ini."
INVALID_REGISTER_USAGE = "Format salah. Gunakan: /register <telegram_id>"
INVALID_UNREGISTER_USAGE = "Format salah. Gunakan: /unreg <telegram_id>"
INVALID_TELEGRAM_ID = "Telegram ID harus berupa angka."
ADMIN_SELF_UNREGISTER_DENIED = "Admin tidak bisa dinonaktifkan."
USER_REGISTERED = "User berhasil didaftarkan."
USER_REACTIVATED = "User berhasil diaktifkan kembali."
USER_ALREADY_ACTIVE = "User sudah aktif."
USER_UNREGISTERED = "User berhasil dinonaktifkan."
USER_ALREADY_INACTIVE = "User sudah nonaktif."
USER_NOT_REGISTERED = "User belum terdaftar."
NO_REGISTERED_USERS = "Belum ada user terdaftar."
USER_NOT_ACTIVE = "Maaf, akun kamu belum terdaftar atau sudah dinonaktifkan."
ASK_FIRST_NAME = (
    "Halo! Akun kamu sudah terdaftar. Sebelum mulai, boleh isi nama depan kamu?"
)
ASK_LAST_NAME = "Terima kasih. Sekarang isi nama belakang kamu."
INVALID_NAME = (
    "Nama harus 2-50 karakter dan hanya boleh berisi huruf, spasi, apostrof, "
    "atau tanda hubung."
)
PARSER_CLARIFICATION = (
    "Maaf, aku belum yakin mencatat transaksi ini. Bisa tulis ulang dengan "
    "format seperti: Bayar parkir 5000?"
)
ADVISOR_MODE_ACTIVE = (
    "Mode AI Advisor aktif. Kamu bisa tanya tentang cashflow, pengeluaran, "
    "budget, atau kebiasaan belanja kamu.\n\n"
    "Untuk kembali mencatat transaksi, ketik /transaction."
)
TRANSACTION_MODE_ACTIVE = (
    "Mode transaksi aktif kembali. Sekarang kamu bisa mencatat pemasukan atau "
    "pengeluaran seperti biasa."
)
ADVISOR_MODE_TIMEOUT_NOTICE = (
    "Mode AI Advisor sudah berakhir karena tidak aktif. Mode transaksi aktif "
    "kembali."
)
ADVISOR_MODE_EXPIRED = (
    "Mode AI Advisor sudah berakhir karena tidak aktif. Mode transaksi aktif "
    "kembali. Kalau ingin bertanya ke advisor lagi, ketik /advisor. Kalau ingin "
    "mencatat transaksi, silakan kirim ulang transaksinya."
)
ADVISOR_UNAVAILABLE = "Layanan advisor sedang tidak tersedia. Coba lagi nanti."


def user_not_active_with_contact(
    telegram_user_id: int,
    admin_contact_telegram: str,
    admin_contact_whatsapp: str,
) -> str:
    return (
        "Maaf, akun kamu belum terdaftar atau sudah dinonaktifkan.\n\n"
        f"Telegram ID kamu: {telegram_user_id}\n\n"
        "Silakan hubungi administrator untuk mendaftarkan akun kamu:\n"
        f"Telegram: {admin_contact_telegram}\n"
        f"WhatsApp: {admin_contact_whatsapp}"
    )


def onboarding_completed(first_name: str) -> str:
    return (
        f"Oke {first_name}, profil kamu sudah lengkap.\n"
        "Sekarang kamu bisa mencatat pemasukan dan pengeluaran.\n"
        "Contoh: Bayar parkir 5000"
    )
