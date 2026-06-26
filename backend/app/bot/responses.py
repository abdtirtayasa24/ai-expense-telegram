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
NORMAL_FLOW_PLACEHOLDER = (
    "Profil kamu sudah lengkap. Fitur pencatatan transaksi akan segera tersedia."
)


def onboarding_completed(first_name: str) -> str:
    return (
        f"Oke {first_name}, profil kamu sudah lengkap.\n"
        "Sekarang kamu bisa mencatat pemasukan dan pengeluaran.\n"
        "Contoh: Bayar parkir 5000"
    )
