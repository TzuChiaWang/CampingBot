from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FloatField, SubmitField
from wtforms.validators import DataRequired


class CampsiteForm(FlaskForm):
    name = StringField("營區名稱", validators=[DataRequired()])
    location = StringField("位置", validators=[DataRequired()])
    altitude = StringField("海拔")
    features = StringField("營區特色")
    WC = StringField("衛浴配置")
    signal_strength = StringField("無線通訊")
    pets = StringField("攜帶寵物規定")
    facilities = StringField("附屬設施")
    sideservice = StringField("附屬服務")
    open_time = StringField("營業時間")
    parking = StringField("停車方式")
    image_url = StringField("圖片網址")
    booking_url = StringField("訂位網址")
    social_url = StringField("社群網址")
    submit = SubmitField("提交")
