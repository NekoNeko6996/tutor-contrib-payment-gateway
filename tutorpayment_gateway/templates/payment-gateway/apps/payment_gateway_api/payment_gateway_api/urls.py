from django.urls import path, re_path
from . import views

app_name = "payment_gateway_api"

urlpatterns = [
    # Giá/Mode (staff-only)
    path("api/course-price/", views.course_price, name="course_price"),
    re_path(r"^api/course/(?P<course_id>.+)/price$", views.course_price_by_path, name="course_price_by_path"),

    # Luồng thanh toán tối thiểu
    path("api/checkout/", views.checkout, name="checkout"),
    path("internal/confirm/", views.confirm, name="confirm"),            # Node gọi về
    path("return/<uuid:uid>/", views.return_page, name="return_page"),   # trang kết quả user
]
