# marketing/models.py

from django.db import models
from django.conf import settings
from django.utils.text import slugify

from core.models import Product 

class Banner(models.Model):
    """
    Represents a promotional banner, typically an image with a link.
    """
    title = models.CharField(max_length=255, help_text="Title of the banner (e.g., 'Summer Sale!')")
    image = models.ImageField(upload_to='marketing/banners/', help_text="Upload the banner image")
    description = models.TextField(blank=True, null=True, help_text="Short description or call to action")
    link_url = models.URLField(max_length=200, blank=True, null=True, help_text="URL to navigate to when banner is clicked")
    display_order = models.IntegerField(default=0, help_text="Order in which banners are displayed (lower number first)")
    is_active = models.BooleanField(default=True, help_text="Whether this banner is currently active and visible")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Banner"
        verbose_name_plural = "Banners"

    def __str__(self):
        return self.title

class AdPlacement(models.Model):
    """
    Defines a specific location on the website where advertisements can be displayed.
    This allows the frontend to request ads for a known 'placement'.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Unique name for the ad placement (e.g., 'Homepage Top Banner', 'Product Detail Sidebar')")
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="URL-friendly identifier for the placement")
    description = models.TextField(blank=True, null=True, help_text="Description of where this ad placement appears")
    is_active = models.BooleanField(default=True, help_text="Whether this placement is currently active and can display ads")

    class Meta:
        ordering = ['name']
        verbose_name = "Ad Placement"
        verbose_name_plural = "Ad Placements"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Advertisement(models.Model):
    """
    Represents an advertisement, linking a specific content type (like a Banner or Product)
    to an AdPlacement. This allows for scheduled and targeted advertising.
    """
    placement = models.ForeignKey(
        AdPlacement,
        on_delete=models.CASCADE,
        related_name='advertisements',
        help_text="The location where this advertisement will be displayed"
    )
    
    # Content type for the advertisement (can be a banner or a specific product)
    banner = models.ForeignKey(
        Banner,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='advertisements',
        help_text="The banner to display for this advertisement (if applicable)"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='advertisements',
        help_text="A featured product to highlight as an advertisement (if applicable)"
    )

    title = models.CharField(max_length=255, blank=True, null=True, help_text="Override title for the advertisement")
    description = models.TextField(blank=True, null=True, help_text="Override description for the advertisement")
    
    start_date = models.DateField(blank=True, null=True, help_text="Date when the advertisement becomes active")
    end_date = models.DateField(blank=True, null=True, help_text="Date when the advertisement becomes inactive")
    
    display_order = models.IntegerField(default=0, help_text="Order in which ads within a placement are displayed")
    is_active = models.BooleanField(default=True, help_text="Whether this advertisement is currently active")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['placement', 'display_order', '-created_at']
        verbose_name = "Advertisement"
        verbose_name_plural = "Advertisements"
        # Ensure only one active ad per placement per content type (optional, but good for control)
        # constraints = [
        #     models.UniqueConstraint(fields=['placement', 'banner'], condition=models.Q(banner__isnull=False, is_active=True), name='unique_active_banner_ad_per_placement'),
        #     models.UniqueConstraint(fields=['placement', 'product'], condition=models.Q(product__isnull=False, is_active=True), name='unique_active_product_ad_per_placement'),
        # ]

    def __str__(self):
        content_name = ""
        if self.banner:
            content_name = f"Banner: {self.banner.title}"
        elif self.product:
            content_name = f"Product: {self.product.name}"
        else:
            content_name = "No Content"
        return f"Ad for {self.placement.name} ({content_name})"

    def clean(self):
        # Ensure only one content type is selected
        if self.banner and self.product:
            raise models.ValidationError("An advertisement cannot have both a banner and a product linked.")
        if not self.banner and not self.product:
            raise models.ValidationError("An advertisement must have either a banner or a product linked.")

    def save(self, *args, **kwargs):
        self.full_clean() # Run clean method before saving
        super().save(*args, **kwargs)
