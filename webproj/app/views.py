from django.http import Http404, HttpResponseRedirect
from django.core.paginator import Paginator, EmptyPage, InvalidPage, PageNotAnInteger
from django.db.models import Count

from app.filters import ProductFilter
from app.forms import *
from app.models import *
import random
from django.contrib.auth import login
import datetime
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect


# Create your views here.
def checkpayments(request, client):
    client_purchases = Purchase.objects.filter(client=client)
    if client_purchases.exists():
        purchases_to_pay = [p for p in client_purchases.all(
        ) if p.available_until != None and p.has_paid_until()]
        # purchases that will expire between today and one week
        today = datetime.datetime.now()
        one_week = today + datetime.timedelta(days=7)
        will_expire = [('{}'.format(pur.product_plan.product.name), '{}'.format(pur.product_plan.product.name)) for pur
                       in purchases_to_pay if today < pur.available_until.replace(tzinfo=None) < one_week]
        return will_expire
    return []


def indexView(request):
    data = {}
    if request.user.is_authenticated and request.user.last_login is not None:
        if request.method == 'POST':

            expiring_choices = request.POST.getlist('expiring_choices')
            if expiring_choices is not None:
                error = False
                client = Client.objects.get(user_id=request.user.id)

                for purch in expiring_choices:
                    purchase = Purchase.objects.get(
                        product_plan__product__name__exact=purch, client_id=client.id)
                    plan = purchase.product_plan
                    if plan.price < client.balance:
                        client.balance -= plan.price
                        if plan.plan_type != 'FREE':
                            if plan.plan_type == 'MONTHLY':
                                purchase.set_paid_until(
                                    datetime_offset_by_months(datetime.datetime.now()))
                            elif plan.plan_type == 'ANNUAL':
                                oneyear = datetime.datetime.now()
                                for i in range(1, 13):
                                    oneyear = datetime_offset_by_months(
                                        oneyear)
                                purchase.set_paid_until(oneyear)
                        client.balance -= plan.price
                        client.save()
                        purchase.save()
                    else:
                        error = True
                        request.session.__setitem__("last_request_error",
                                                    "Insufficient balance for some of the products!")
                if not error:
                    request.session.__setitem__(
                        "last_request_success", "Success in the completion of the purchase!")
            return redirect('index')

        else:
            if request.user.last_login.replace(tzinfo=None, microsecond=0) == datetime.datetime.now().replace(microsecond=0):
                client = Client.objects.get(user_id=request.user.id)
                will_expire = checkpayments(request, client)
                form = Expiring_Products_Form(expiring_choices=will_expire)
                data['will_expire'] = form
                data['expire_modal'] = will_expire

    if request.method == 'GET':
        products_banner = []

        for _ in range(random.randint(2, 6)):
            index = random.randint(0, Product.objects.count()-1)
            prod = Product.objects.all()[index]
            if prod not in products_banner:
                products_banner.append(prod)

        # Vai contar o nº de ocorrências noutra tabela e ordenar pelas ocorrências
        best_sellers_plans = Product_Pricing_Plan.objects.annotate(
            numVendasProd=Count('purchase')).order_by('-numVendasProd')

        best_sellers = []
        for plan in best_sellers_plans[:6]:
            best_sellers.append(plan.product)

        for best in best_sellers:
            best.tags = "best"

        new_arrivals = Product.objects.all().order_by('-id')

        new_arrivals_distinct = []

        count = 0
        for arrival in new_arrivals:
            if count == 6:
                break
            if arrival not in best_sellers:
                arrival.tags = "new"
                arrival.new = True
                new_arrivals_distinct.append(arrival)
                count += 1
            else:
                index = best_sellers.index(arrival)
                best_sellers[index].new = True
                best_sellers[index].tags += " new"

        products = new_arrivals_distinct + best_sellers
        for product in products:
            product.Roundprice = round(
                product.price, 2)
            product.nStars = range(product.stars)
            product.nEmptyStars = range(5 - product.stars)
        data['products'] = products
        data['productsBanner'] = products_banner
        data['activelem'] = 'home'

        if request.session.get("last_request_error") is not None:
            data["errors"] = request.session.get("last_request_error")
            del request.session["last_request_error"]
        if request.session.get("last_request_success") is not None:
            data["successes"] = request.session.get("last_request_success")
            del request.session["last_request_success"]

    return render(request, 'index.html', data)


def shopView(request):
    products = ProductFilter(request.GET, queryset=Product.objects.all()).qs
    order = request.GET.get('order')
    if order:
        if order == 'cost':
            products = sorted(products, key=lambda p: p.price)
        elif order == '-cost':
            products = sorted(products, key=lambda p: p.price, reverse=True)
        elif order == 'rate':
            products = sorted(products, key=lambda p: p.stars)
        elif order == '-rate':
            products = sorted(products, key=lambda p: p.stars, reverse=True)
    else:
        products = sorted(products, key=lambda p: p.price)

    products, page = getPaginator(request, products, 12)

    categories = Category.objects.all()

    developers = Developer.objects.all()

    for category in categories:
        category.numProd = Product.objects.filter(
            category__exact=category).count()

    for product in products:
        product.roundPrice = product.price
        product.nStars = range(product.stars)
        product.nEmptyStars = range(5 - product.stars)

    data = {'activelem': 'shop', 'products': products, 'page': page,
            'categories': categories, 'developers': developers, 'getParams': request.GET}
    if request.session.get("last_request_error") is not None:
        data["errors"] = request.session.get("last_request_error")
        del request.session["last_request_error"]

    return render(request, 'shop.html',
                  data)


def register(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            client = Client(user=user)
            client.save()
            user.refresh_from_db()
            return redirect('index')
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})


def datetime_offset_by_months(datetime_origin, n=1):

    one_day = datetime.timedelta(days=1)
    q, r = divmod(datetime_origin.month + n, 12)

    datetime_offset = datetime.datetime(
        datetime_origin.year + q, r + 1, 1) - one_day

    if datetime_origin.month != (datetime_origin + one_day).month:
        return datetime_offset

    if datetime_origin.day >= datetime_offset.day:
        return datetime_offset

    return datetime_offset.replace(day=datetime_origin.day)

# class used to process valid forms in the products view
class Products_Forms_Processing:

    def __init__(self, client, product):
        self.client = client
        self.product = product

    def check_curr_form(self, form, request):
        if isinstance(form, PurchaseForm):
            return self.payment_form_process(form, request)
        elif isinstance(form, FavoritesForm):
            return self.favorites_form_process(form, request)
        else:
            return Http404("Something went wrong")

    def payment_form_process(self, form, request):
        paymenttype = form.cleaned_data.get("paymenttype")
        valuetopay = Product_Pricing_Plan.objects.get(id=paymenttype)
        p = Purchase.objects.filter(
            client=self.client, product_plan__product_id=self.product)
        # check if client has already the product
        if p.exists() and p[0].has_paid_until():
            request.session.__setitem__(
                "last_request_error", "You already have this product!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        # check if the client has enough balance
        elif self.client.balance < valuetopay.price:
            request.session.__setitem__(
                "last_request_error", "You do not have enough credit to complete the purchase!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        # process the purchase
        else:
            p = Purchase(client=self.client, product_plan_id=paymenttype)
            if valuetopay.plan_type != 'FREE':
                if valuetopay.plan_type == 'MONTHLY':
                    p.set_paid_until(datetime_offset_by_months(
                        datetime.datetime.now()))
                elif valuetopay.plan_type == 'ANNUAL':
                    oneyear = datetime.datetime.now()
                    for i in range(1, 13):
                        oneyear = datetime_offset_by_months(oneyear)
                    p.set_paid_until(oneyear)
            self.client.balance -= valuetopay.price
            self.client.save()

            p.save()
            request.session.__setitem__(
                "last_request_success", "Success in the completion of the purchase!")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def favorites_form_process(self, form, request):
        client_favorites = self.client.favorites.all()
        if self.product not in client_favorites:
            self.client.favorites.add(self.product)
            request.session.__setitem__(
                "last_request_success", "Product " + self.product.name + " successfully added to your favorites!")
        else:
            self.client.favorites.remove(self.product)
            request.session.__setitem__("last_request_success", "Product " +
                                        self.product.name + " successfully removed to your favorites!")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def prodDetails(request, idprod):
    product = Product.objects.get(id=idprod)
    if request.user.is_authenticated:
        client = Client.objects.get(user_id=request.user.id)
        if request.method == "POST":
            form_purchases, form_favorites = PurchaseForm(
                request.POST), FavoritesForm(request.POST)
            response = None
            handler = Products_Forms_Processing(client, product)
            if form_purchases.is_valid():
                response = handler.check_curr_form(form_purchases, request)
            elif form_favorites.is_valid():
                handler = Products_Forms_Processing(client, product)
                response = handler.check_curr_form(form_favorites, request)
            return response
        else:
            form_purchases, form_favorites = PurchaseForm(), FavoritesForm()
            reviews = Reviews.objects.filter(product=product).order_by('-date')
            numreviews = reviews.count()
            # --- Django Pagination ---
            paginator = Paginator(reviews, 5)
            page_number = request.GET.get('page')
            page_obj = paginator.get_page(page_number)
            # ------------------------
            # check if product is already, or not, added to the client's favorites
            is_fav = False
            if product in client.favorites.all():
                is_fav = True
            has_reviewed = False
            for review in page_obj.object_list:
                review.nStars = range(int(review.rating))
                review.nEmptyStars = range(5 - int(review.rating))

                if review.author.id == client.id:
                    has_reviewed = True

            rate = reviews.aggregate(Avg('rating'))['rating__avg']
            if rate:
                product.rate = rate
            else:
                product.rate = 0
            product.nStars, product.nEmptyStars = range(
                int(product.rate)), range(5 - int(product.rate))
            productbenefits = Prod_Benefits.objects.filter(product=product)
            pricing = Product_Pricing_Plan.objects.filter(product=product)
            totalpurchases = Purchase.objects.filter(
                product_plan__product=product).count()
            data = {'prod': product, 'revs': page_obj, 'prodbenefs': productbenefits,
                    'plans': pricing, 'purch': totalpurchases, 'numreviews': numreviews, 'form_purch': form_purchases,
                    ' form_fav': form_favorites, 'is_fav': is_fav, 'has_rev': has_reviewed}
            # render in template errors in forms

            if request.session.get("last_request_error") is not None:
                data["errors"] = request.session.get("last_request_error")
                del request.session["last_request_error"]
            if request.session.get("last_request_success") is not None:
                data["successes"] = request.session.get("last_request_success")
                del request.session["last_request_success"]
            return render(request, 'productdetails.html', data)
    else:
        request.session.__setitem__("last_request_error",
                                    "Need to be logged in to view product!")
        return redirect('shop')

# view for adding or editing a custom review


def review_View(request, idprod):
    client = Client.objects.filter(user_id=request.user.id)[0]
    review = Reviews.objects.filter(author__id=client.id, product_id=idprod)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            if review.exists():
                rev = review[0]
                rev.date = datetime.date.today()
                rev.rating = form.cleaned_data['rating']
                rev.body = form.cleaned_data['text']
                rev.save()
                request.session.__setitem__(
                    "last_request_success", "Your review was successfully updated!")
            else:
                review = Reviews(author=client, product_id=idprod)
                review.rating = form.cleaned_data['rating']
                review.body = form.cleaned_data['text']
                review.save()
                request.session.__setitem__(
                    "last_request_success", "Your review was successfully added!")
            return redirect('productdetails', idprod=idprod)
    else:
        if review.exists():
            form = fill_review_form(review[0])
        else:
            form = ReviewForm()
    return render(request, 'reviewsubmission.html', {'form': form})


# in case the we a client is editing a review that he made
def fill_review_form(rev):
    form = ReviewForm()
    form.fields['rating'].initial = rev.rating
    form.fields['text'].initial = rev.body
    return form


# fill initial field for the client form
def fill_form(client):
    form = UpdateClientForm()
    form.fields['username'].initial = client.user.username
    form.fields['first_name'].initial = client.user.first_name
    form.fields['last_name'].initial = client.user.last_name
    form.fields['email'].initial = client.user.email
    return form


def accountDetails(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            is_superuser = True
        else:
            is_superuser = False

        user = User.objects.get(username=request.user.username)
        client = Client.objects.get(user_id=user.id)

        client_purch, page_purch = getPaginator(request, Purchase.objects.filter(
            client_id=client.id).order_by('-available_until'), 10, 'page_purch')
        # favourites
        fav, page_fav = getPaginator(
            request, client.favorites.all(), 10, 'page_fav')
        data = {'userClient': client, 'favourites': fav, 'is_superuser': is_superuser,
                'client_purch': client_purch, 'page_purch': page_purch, 'page_fav': page_fav}
        if request.method == "POST":
            form = UpdateClientForm(request.POST, instance=request.user)
            form_pw = UpdatePasswordForm(request.user, request.POST)
            if 'old_password' not in request.POST:
                if form.is_valid():
                    update = form.save()
                    update.client = request.user
                    client = Client.objects.get(user_id=update.client.id)
                    update.save()
                    update.refresh_from_db()
                    login(request, update.client)
                    form = fill_form(client)
                    form_pw = UpdatePasswordForm(request.user)
                    data['form'], data['form_pw'] = form, form_pw
                    data['success'] = 'Success Updating the General Information of your Account!'

                    return render(request, 'clientdetails.html', data)

                elif not form_pw.is_valid():
                    form_pw = UpdatePasswordForm(request.user)
                    data['form'] = form
                    data['form_pw'] = form_pw
                    data['error'] = 'There was an Error updating the General Information of your Account. Please Check bellow the details'
            else:
                if form_pw.is_valid():
                    user = form_pw.save()
                    update_session_auth_hash(request, form_pw.user)
                    user.client = request.user
                    client = Client.objects.get(user_id=user.client.id)
                    user.save()
                    user.refresh_from_db()
                    # to stay logged in
                    # Because after changes in account, the system logout the user
                    form = fill_form(client)
                    login(request, user.client)
                    data['form'], data['form_pw'] = form, form_pw
                    data['success'] = 'Success Updating your Password!'

                    return render(request, 'clientdetails.html', data)

                elif not form.is_valid():
                    form = fill_form(client)
                    data['form'] = form
                    data['form_pw'] = form_pw
                    data['error'] = 'There was an Error updating your Password. Please Check bellow the details'

        else:
            form = fill_form(client)
            form_pw = UpdatePasswordForm(request.user)

            data['form'], data['form_pw'] = form, form_pw

        return render(request, 'clientdetails.html', data)
    else:
        return redirect('/login')


def adminPurchases(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            purchases, page = getPaginator(
                request, Purchase.objects.all().order_by('-id'), 10)
            return render(request, 'adminpurchases.html',
                          {'purchases': purchases, 'page': page})
        else:
            return redirect('notfound')
    else:
        return redirect('/login')


def adminUsers(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            data = {}
            if request.method == 'POST':
                form = AddBalanceForm(request.POST)
                if form.is_valid():
                    username = form.cleaned_data['user']
                    user = User.objects.get(username=username)
                    client = Client.objects.get(user_id=user.id)
                    cur_balance = client.balance
                    client.balance = cur_balance + form.cleaned_data['balance']
                    client.save()
                    data['success'] = 'Success editing the product ' + \
                        user.username
                else:
                    data['error'] = True
            else:
                form = AddBalanceForm()

            users, page = getPaginator(
                request, Client.objects.all().order_by('-id'), 10)

            data['users'], data['form'], data['page'] = users, form, page
            return render(request, 'adminusers.html', data)

        else:
            return redirect('notfound')
    else:
        return redirect('/login')


def adminApps(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            data = {}
            if request.method == 'POST':
                form = EditProductForm(request.POST)
                if form.is_valid():
                    idprod = form.cleaned_data['prod']
                    product = Product.objects.filter(id=idprod)[0]
                    product.name = form.cleaned_data['name']
                    product.icon = form.cleaned_data['icon']
                    product.description = form.cleaned_data['description']

                    categ = form.cleaned_data['category']
                    cats_list = Category.objects.filter(title=categ)
                    for c in cats_list:
                        product.category.add(c)

                    product.developer = form.cleaned_data['developer']
                    product.save()
                    data['success'] = 'Success editing the product ' + product.name
                else:
                    data['error'] = True
            else:
                form = EditProductForm()

            products, page = getPaginator(
                request, Product.objects.all().order_by('-id'), 10)

            data['products'], data['form'], data['page'] = products, form, page
            return render(request, 'adminapps.html', data)
        else:
            return redirect('notfound')
    else:
        return redirect('/login')


def adminDevs(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            data = {}
            if request.method == 'POST':
                form = AddDeveloper(request.POST)
                if form.is_valid():
                    form.save()
                    data['success'] = 'Success adding the developer!'
                else:
                    data['error'] = 'The developer already exists!'
            else:
                form = AddDeveloper()

            data['form'] = form
            return render(request, 'admindevs.html', data)
        else:
            return redirect('notfound')
    else:
        return redirect('/login')


def adminCat(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            data = {}
            if request.method == 'POST':
                form = AddCategory(request.POST)
                if form.is_valid():
                    form.save()
                    data['success'] = 'Success adding the category!'
                else:
                    data['error'] = 'The category already exists!'
            else:
                form = AddCategory()

            data['form'] = form
            return render(request, 'admincat.html', data)
        else:
            return redirect('notfound')
    else:
        return redirect('/login')


def handler404(request):
    response = render(request, 'notfound.html')
    response.status_code = 404
    return response


def aboutus(request):
    return render(request, "about.html")


def addApp(request):
    if request.user.is_authenticated and request.user.is_superuser:
        data = {}
        if request.method == 'POST':
            form = AddProductForm(request.POST)
            form_plan = AddPricingPlan(request.POST)
            data['form'] = form
            data['form_plan'] = form_plan
            if form.is_valid() and form_plan.is_valid():
                if form_plan.cleaned_data['price'] > 0.00 and form_plan.cleaned_data['plan'] == 'FREE':
                    data['error'] = "You cannot add Price to a Free plan Type!"
                elif form_plan.cleaned_data['price'] == 0.00 and form_plan.cleaned_data['plan'] != 'FREE':
                    data['error'] = "You have to add Price to monthly or annual plans!"
                else:
                    form.save()
                    app_name = form.cleaned_data['name']
                    app = Product.objects.filter(name=app_name)[0]
                    pricing_plan = Product_Pricing_Plan(product=app)
                    pricing_plan.plan_type = form_plan.cleaned_data['plan']
                    pricing_plan.price = form_plan.cleaned_data['price']
                    pricing_plan.feature = form_plan.cleaned_data['feature']
                    pricing_plan.save()
                    data['success'] = 'Sucessing adding new App!'

            else:
                data['error'] = 'Some error Ocurred. Check bellow for details'

        if 'error' not in data:
            data['form'] = AddProductForm()
            data['form_plan'] = AddPricingPlan()

        return render(request, 'addapp.html', data)
    return redirect('notfound')


def getPaginator(request, qs, per_page, request_page='page'):
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get(request_page)
    page = paginator.get_page(page_number)

    try:
        qs = paginator.page(page_number)
    except PageNotAnInteger:
        qs = paginator.page(1)
    except EmptyPage:
        qs = []
    except InvalidPage:
        return redirect('notfound')

    return qs, page
