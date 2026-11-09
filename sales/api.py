from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from masters.models import Product
from masters.serializers import ProductSerializer
from inventory.services import confirm_sales_order, cancel_sales_order, InventoryError
from .models import SalesOrder
from .serializers import (
    SalesOrderReadSerializer,
    OrderCreateInputSerializer,
)
from .services import create_sales_order, OrderValidationError


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductListAPIView(APIView):
    """
    GET /api/products/
    Lists active products with optional search query and pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.GET.get('search', '').strip()
        products = Product.objects.filter(status=Product.Status.ACTIVE)

        if query:
            products = products.filter(
                Q(code__icontains=query) |
                Q(name__icontains=query) |
                Q(category__icontains=query)
            )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class OrderListCreateAPIView(APIView):
    """
    POST /api/orders/ - Create a new Draft sales order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation error', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        try:
            order = create_sales_order(
                customer_id=validated_data['customer_id'],
                items_data=validated_data['items'],
                discount_percentage=validated_data.get('discount_percentage'),
                user=request.user,
            )
            read_serializer = SalesOrderReadSerializer(order)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)
        except OrderValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Failed to create order: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailAPIView(APIView):
    """
    GET /api/orders/{id}/
    Retrieves accessible order and its items.
    Enforces role-based permissions: Sales user cannot access another user's order.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = SalesOrder.objects.select_related('customer', 'created_by').prefetch_related('items__product').get(pk=pk)
        except SalesOrder.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Security check: sales user can only view their own orders
        if not request.user.is_admin and order.created_by != request.user:
            return Response(
                {'error': 'Permission denied. You cannot access orders created by another user.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SalesOrderReadSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderConfirmAPIView(APIView):
    """
    POST /api/orders/{id}/confirm/
    Confirms an order and deducts stock with transactional concurrency lock.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = SalesOrder.objects.get(pk=pk)
        except SalesOrder.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_admin and order.created_by != request.user:
            return Response(
                {'error': 'Permission denied. You cannot confirm this order.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            confirmed_order = confirm_sales_order(order.id, request.user)
            serializer = SalesOrderReadSerializer(confirmed_order)
            return Response(
                {
                    'message': f"Order {confirmed_order.order_number} confirmed successfully.",
                    'order': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except InventoryError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Confirmation failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class OrderCancelAPIView(APIView):
    """
    POST /api/orders/{id}/cancel/
    Cancels an order and restores stock if it was previously confirmed.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = SalesOrder.objects.get(pk=pk)
        except SalesOrder.DoesNotExist:
            return Response({'error': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_admin and order.created_by != request.user:
            return Response(
                {'error': 'Permission denied. You cannot cancel this order.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            cancelled_order = cancel_sales_order(order.id, request.user)
            serializer = SalesOrderReadSerializer(cancelled_order)
            return Response(
                {
                    'message': f"Order {cancelled_order.order_number} cancelled successfully.",
                    'order': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except InventoryError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f"Cancellation failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
