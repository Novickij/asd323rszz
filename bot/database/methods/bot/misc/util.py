import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    admin_tg_ids: list
    month_cost: list
    auto_extension: bool = False
    trial_period: int
    UTC_time: int
    max_people_server: int
    limit_ip: int
    limit_GB: int
    tg_token: str
    yoomoney_token: str
    yoomoney_wallet_token: str
    tg_wallet_token: str = ''
    lava_token_secret: str
    lava_id_project: str
    yookassa_shop_id: str
    yookassa_secret_key: str
    yookassa_return_url: str
    cryptomus_key: str
    cryptomus_uuid: str
    referral_day: int
    referral_percent: int
    minimum_withdrawal_amount: int
    COUNT_SECOND_DAY: int = 86400
    COUNT_SECOND_MOTH: int = 2678400
    languages: str
    name: str
    id_channel: str  # Удалено дублирование int
    link_channel: str = ''
    crypto_bot_api: str = ''
    debug: bool = False
    postgres_db: str
    postgres_user: str
    postgres_password: str
    max_count_groups: int = 100
    import_bd: int = 0
    check_follow: bool = False
    token_stars: str
    type_payment: dict = {
        0: 'new_key',
        1: 'extend_key',
        2: 'donate',
        3: 'switch'
    }
    type_buttons_mailing: list = [
        'vpn_connect_btn',
        'donate_btn',
        'language_btn',
        'help_btn',
        'promokod_btn',
        'affiliate_btn',
        'about_vpn_btn',
        'general_menu_btn',
        'not_button_mailing_btn'
    ]
    free_switch_location: int
    price_switch_location_type: int
    name_channel: str
    free_vpn: int
    limit_gb_free: int
    font_template: str = ''
    support_tg: str = 'https://t.me/WolfPN_Support'

    def __init__(self):
        self.read_evn()

    def is_admin(self, id_user) -> bool:
        return id_user in self.admin_tg_ids

    def read_evn(self):
        admin_ids = os.getenv('ADMIN_TG_IDS')
        if not admin_ids:
            raise ValueError('Write your IDs Telegram to ADMIN_TG_IDS')
        self.admin_tg_ids = [int(id.strip()) for id in admin_ids.split(',')]

        self.tg_token = os.getenv('TG_TOKEN')
        if not self.tg_token:
            raise ValueError('Write your TOKEN TelegramBot to TG_TOKEN')

        self.name = os.getenv('NAME')
        if not self.name:
            raise ValueError('Write your name bot to NAME')

        check_follow = os.getenv('CHECK_FOLLOW', '')
        if check_follow == '':
            raise ValueError('Write your check follow to CHECK_FOLLOW')
        self.check_follow = bool(int(check_follow))

        self.id_channel = os.getenv('ID_CHANNEL', '')
        if self.check_follow and not self.id_channel:
            raise ValueError('Write your ID channel to ID_CHANNEL')

        self.link_channel = os.getenv('LINK_CHANNEL', '')
        if self.check_follow and not self.link_channel:
            raise ValueError('Write your link channel to LINK_CHANNEL')

        self.name_channel = os.getenv('NAME_CHANNEL', '')
        if self.check_follow and not self.name_channel:
            raise ValueError('Write your name channel to NAME_CHANNEL')

        self.languages = os.getenv('LANGUAGES')
        if not self.languages:
            raise ValueError('Write your languages bot to LANGUAGES')

        price_switch_location_type = os.getenv('PRICE_SWITCH_LOCATION')
        if not price_switch_location_type:
            raise ValueError('Enter the price for changing the key location to PRICE_SWITCH_LOCATION')
        self.price_switch_location_type = int(price_switch_location_type)

        try:
            month_cost = os.getenv('MONTH_COST')
            if not month_cost:
                raise ValueError('Write your price month to MONTH_COST')
            self.month_cost = month_cost.split(',')
        except Exception as e:
            raise ValueError('You filled in the MONTH_COST field incorrectly', e)

        trial_period = os.getenv('TRIAL_PERIOD', '')
        if trial_period == '':
            raise ValueError('Write your time trial period sec to TRIAL_PERIOD')
        self.trial_period = int(trial_period)

        free_switch_location = os.getenv('FREE_SWITCH_LOCATION', '')
        if free_switch_location == '':
            raise ValueError('Write your free switch location min 1 to FREE_SWITCH_LOCATION')
        if int(free_switch_location) <= 0:
            raise ValueError('Write your free switch location min 1 to FREE_SWITCH_LOCATION')
        self.free_switch_location = int(free_switch_location)

        utc_time = os.getenv('UTC_TIME', '')
        if utc_time == '':
            raise ValueError('Write your UTC TIME to UTC_TIME')
        self.UTC_time = int(utc_time)

        referral_day = os.getenv('REFERRAL_DAY', '')
        if referral_day == '':
            raise ValueError('Write your day per referral to REFERRAL_DAY')
        self.referral_day = int(referral_day)

        referral_percent = os.getenv('REFERRAL_PERCENT', '')
        if referral_percent == '':
            raise ValueError('Write your percent per referral to REFERRAL_PERCENT')
        self.referral_percent = int(referral_percent)

        minimum_withdrawal_amount = os.getenv('MINIMUM_WITHDRAWAL_AMOUNT', '')
        if minimum_withdrawal_amount == '':
            raise ValueError('Write your minimum withdrawal amount to MINIMUM_WITHDRAWAL_AMOUNT')
        self.minimum_withdrawal_amount = int(minimum_withdrawal_amount)

        free_vpn = os.getenv('FREE_SERVER', '')
        if free_vpn == '':
            raise ValueError('Write your FREE_SERVER')
        self.free_vpn = int(free_vpn)

        limit_gb_free = os.getenv('LIMIT_GB_FREE', '')
        if self.free_vpn and limit_gb_free == '':
            raise ValueError('Write your limit gb free server to LIMIT_GB_FREE')
        self.limit_gb_free = int(limit_gb_free)

        limit_ip = os.getenv('LIMIT_IP', '')
        self.limit_ip = int(limit_ip) if limit_ip else 0

        limit_gb = os.getenv('LIMIT_GB', '')
        self.limit_GB = int(limit_gb) if limit_gb else 0

        import_bd = os.getenv('IMPORT_DB', '')
        self.import_bd = int(import_bd) if import_bd else 0

        token_stars = os.getenv('TG_STARS', '')
        self.token_stars = '' if token_stars != 'off' else token_stars
        token_stars_dev = os.getenv('TG_STARS_DEV', '')
        self.token_stars = '' if token_stars_dev == 'run' else self.token_stars

        self.yoomoney_token = os.getenv('YOOMONEY_TOKEN', '')
        self.yoomoney_wallet_token = os.getenv('YOOMONEY_WALLET', '')
        self.lava_token_secret = os.getenv('LAVA_TOKEN_SECRET', '')
        self.lava_id_project = os.getenv('LAVA_ID_PROJECT', '')

        self.yookassa_shop_id = os.getenv('YOOKASSA_SHOP_ID', '')
        if not self.yookassa_shop_id:
            raise ValueError('Write your YooKassa shop ID to YOOKASSA_SHOP_ID')

        self.yookassa_secret_key = os.getenv('YOOKASSA_SECRET_KEY', '')
        if not self.yookassa_secret_key:
            raise ValueError('Write your YooKassa secret key to YOOKASSA_SECRET_KEY')

        self.yookassa_return_url = os.getenv('YOOKASSA_RETURN_URL', '')
        if not self.yookassa_return_url:
            raise ValueError('Write your YooKassa return URL to YOOKASSA_RETURN_URL')

        self.cryptomus_key = os.getenv('CRYPTOMUS_KEY', '')
        self.cryptomus_uuid = os.getenv('CRYPTOMUS_UUID', '')
        self.crypto_bot_api = os.getenv('CRYPTO_BOT_API', '')
        self.font_template = os.getenv('FONT_TEMPLATE', '')
        self.debug = os.getenv('DEBUG', 'False') == 'True'

        self.postgres_db = os.getenv('POSTGRES_DB', '')
        if not self.postgres_db:
            raise ValueError('Write your name DB to POSTGRES_DB')

        self.postgres_user = os.getenv('POSTGRES_USER', '')
        if not self.postgres_user:
            raise ValueError('Write your login DB to POSTGRES_USER')

        self.postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        if not self.postgres_password:
            raise ValueError('Write your password DB to POSTGRES_PASSWORD')

        pg_email = os.getenv('PGADMIN_DEFAULT_EMAIL', '')
        if not pg_email:
            raise ValueError('Write your email to PGADMIN_DEFAULT_EMAIL')

        pg_password = os.getenv('PGADMIN_DEFAULT_PASSWORD', '')
        if not pg_password:
            raise ValueError('Write your password to PGADMIN_DEFAULT_PASSWORD')

        self.support_tg = os.getenv('SUPPORT_TG', 'https://t.me/WolfPN_Support')

CONFIG = Config()