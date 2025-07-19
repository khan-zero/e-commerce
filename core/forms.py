from django import forms
from django.forms import inlineformset_factory
from .models import Order, Product, Shop, ProductImage, CustomUser

class OrderStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'category', 'available', 'shop']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            # If the user is a seller, hide the shop field and pre-fill it
            self.fields['shop'].widget = forms.HiddenInput()
            try:
                self.initial['shop'] = user.shop_profile.id
            except Shop.DoesNotExist:
                pass # Handle case where seller has no shop (should be caught by view permission)

class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'is_main']

# Formset for managing product images related to a product
ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage, 
    form=ProductImageForm, 
    extra=1, # Number of empty forms to display
    can_delete=True, # Allow deleting existing images
    fields=['image', 'is_main']
)

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['name', 'description', 'logo', 'is_active']

class CustomUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'is_active', 'is_staff', 'is_seller']