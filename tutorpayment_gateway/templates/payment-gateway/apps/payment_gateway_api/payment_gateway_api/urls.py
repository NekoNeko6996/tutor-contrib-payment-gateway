from django.urls import path, re_path
from . import views

app_name = "payment_gateway_api"

urlpatterns = [
    path("api/course-price", views.course_price, name="course_price"),
    re_path(r"^api/course/(?P<course_id>.+)/price$", views.course_price_by_path, name="course_price_by_path"),
]
