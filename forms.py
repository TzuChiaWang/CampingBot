from random import choice
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, URL, Optional


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class CampsiteForm(FlaskForm):
    name = StringField("營區名稱", validators=[DataRequired(message="請輸入營區名稱")])
    location = StringField("位置", validators=[DataRequired(message="請輸入營區地址")])
    altitude = StringField("海拔", validators=[DataRequired(message="請輸入營區海拔")])
    features = StringField("營區特色", validators=[DataRequired(message="請輸入營區特色")])
    WC = StringField("衛浴配置")
    signal_strength = MultiCheckboxField("無線通訊", 
                                     choices=[
                                         ("中華電信", "中華電信"),
                                         ("遠傳", "遠傳"),
                                         ("台哥大", "台哥大"),
                                         ("亞太", "亞太"),
                                         ("WIFI", "WIFI"),
                                         ("無資訊", "無資訊"),
                                     ],
                                     validators=[DataRequired(message="請至少選擇一個通訊選項")])
    pets = SelectField("攜帶寵物規定", 
                      choices=[
                          ("全區不可帶寵物", "全區不可帶寵物"),
                          ("自搭帳可帶寵物", "自搭帳可帶寵物")
                      ],
                      validators=[DataRequired(message="請選擇寵物規定")])
    facilities = StringField("附屬設施", validators=[DataRequired(message="請輸入附屬設施")])
    sideservice = StringField("附屬服務")
    open_time = StringField("營業時間")
    parking = SelectField("停車方式", 
                       choices=[
                           ("車停營位旁", "車停營位旁"),
                           ("集中停車", "集中停車")
                       ],
                       validators=[DataRequired(message="請選擇停車方式")])
    image_url = StringField("圖片網址", validators=[DataRequired(message="請輸入至少一個圖片網址")])
    booking_url = StringField("訂位網址", validators=[DataRequired(message="請輸入訂位網址"), URL(message="請輸入有效的網址")])
    social_url = StringField("社群網址", validators=[Optional(), URL(message="請輸入有效的網址")])
    submit = SubmitField("提交")
