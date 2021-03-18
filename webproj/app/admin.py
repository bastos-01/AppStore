from django.contrib import admin
from app.models import *
# Register your models here.

admin.site.register(Client)
admin.site.register(Developer)
admin.site.register(Category)
admin.site.register(Purchase)
admin.site.register(Product)
admin.site.register(Prod_Benefits)
admin.site.register(Reviews)
admin.site.register(Product_Pricing_Plan)

