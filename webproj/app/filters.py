import django_filters
from django_property_filter import PropertyFilterSet, PropertyNumberFilter, PropertyOrderingFilter
from app.models import Product


class ProductFilter(PropertyFilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains', exclude='')
    max_price = PropertyNumberFilter(field_name='price', lookup_expr='lt')
    min_price = PropertyNumberFilter(field_name='price', lookup_expr='gte')
    cost = PropertyNumberFilter(field_name='price')
    rate = PropertyNumberFilter(field_name='stars')

    ''' When ordering filter, it ignores the filters before if they are properties because they return lists and this ordering filter uses the queryset.
    Being the last of the execution, and never filtering list, it will not acess to the lists filtered but to the last queryset filtered from filters of fields of the model
    order = PropertyOrderingFilter(
        fields=(
            ('price', 'cost'),
            ('stars', 'rate'),
        )
    )
    '''


    class Meta:
        model = Product
        fields = ['max_price', 'min_price', 'rate', 'category', 'developer', 'name']

