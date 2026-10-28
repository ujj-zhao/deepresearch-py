"""全局常量：Redis 键模板等。

过期时间等可配置项统一放 core/config.py（settings），此处只放键模板。
"""

# 验证码答案（值为答案字符串），对齐若依 CacheConstants.CAPTCHA_CODE_KEY
CAPTCHA_CODE_KEY = "captcha_codes:{}"
# 验证码校验通过标记（独立校验接口与登录之间的衔接），值为 "1"
CAPTCHA_PASSED_KEY = "captcha_passed:{}"

# 过期时间
CAPTCHA_EXPIRE = 120

LOGIN_TOKEN_KEY = "login_tokens:"

# 系统配置缓存键（值为配置值字符串），对齐若依 CacheConstants.SYS_CONFIG_KEY
SYS_CONFIG_KEY = "sys_config:{}"

# 字典数据缓存键（值为 DictData 列表 JSON），对齐若依 CacheConstants.SYS_DICT_KEY
SYS_DICT_KEY = "sys_dict:{}"

# IP 归属地缓存键（值为 "国家 省份 城市" 字符串）
IP_LOCATION_KEY = "ip_location:{}"

# 登录日志状态（对齐若依 Constants.LOGIN_SUCCESS / LOGIN_FAIL）
LOGIN_SUCCESS = "0"
LOGIN_FAIL = "1"

# 密码重试错误计数键（值为次数字符串），对齐若依 CacheConstants.PWD_ERR_CNT_KEY
PWD_ERR_CNT_KEY = "pwd_err_cnt:{}"

# 登录会话缓存键（值为 LoginUser JSON），对齐若依 CacheConstants.LOGIN_TOKENKEY
LOGIN_TOKEN_KEY = "login_tokens:{}"


#用户名长度限制
USERNAME_MIN_LENGTH = 2
USERNAME_MAX_LENGTH = 20

#密码长度限制
PASSWORD_MIN_LENGTH = 5
PASSWORD_MAX_LENGTH = 20
