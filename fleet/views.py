import calendar
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from django.db import transaction
import os
from rest_framework import generics
from django.conf import settings
from django.utils.timezone import now
from reportlab.pdfgen import canvas
from rest_framework.decorators import api_view

import requests
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from fleet.models import (User, VehicleService, ServiceType,
                          SubService, VehiclePart, Vehicle)
from fleet.serializers import (CustomTokenObtainPairSerializer, UserSerializer, SubServiceSerializer,
                               ServiceTypeSerializer, VehiclePartSerializer, VehicleServiceSerializer, VehicleSerializer)


class CustomObtainTokenPairView(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        user = self.request.user
        if not user.is_superuser:
            # Return only the current logged-in user if not a superuser
            return User.objects.filter(id=user.id)
        else:
            # Return all users if the request is made by a superuser
            return User.objects.all()


class CurrentUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return User.objects.filter(id=user.id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ServiceTypeViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceTypeSerializer
    queryset = ServiceType.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class SubServiceViewSet(viewsets.ModelViewSet):
    serializer_class = SubServiceSerializer
    queryset = SubService.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class VehiclePartViewSet(viewsets.ModelViewSet):
    serializer_class = VehiclePartSerializer
    queryset = VehiclePart.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter the queryset based on the logged-in user
        user = self.request.user
        if user.user_type == "mechanic" and not user.is_superuser:
            return VehiclePart.objects.filter(mechanic=user)
        elif user.is_superuser:
            return VehiclePart.objects.all()
        else:
            # Return an empty queryset for non-mechanics who are not superusers
            return VehiclePart.objects.none()


class VehicleServiceViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleServiceSerializer
    queryset = VehicleService.objects.all()
    permission_classes = [permissions.IsAuthenticated]


class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter the queryset based on the logged-in user
        user = self.request.user
        if user.user_type == "mechanic" and not user.is_superuser:
            return Vehicle.objects.filter(mechanic=user)
        elif user.is_superuser:
            return Vehicle.objects.all()
        else:
            # Return an empty queryset for non-mechanics who are not superusers
            return Vehicle.objects.none()


class GeneratePDF(APIView):
    def get(self, request):
        # Create an in-memory PDF file
        buffer = BytesIO()

        # Set up the PDF document
        pdf = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Fetch vehicle data using VehicleSerializer
        vehicles = Vehicle.objects.all()
        vehicle_serializer = VehicleSerializer(vehicles, many=True)

        # Create tables to display the serialized data
        vehicle_data = [['Plate Number',
                         'Vehicle Status', 'Type', 'Model', 'Engine Number', 'Color']]
        for vehicle_data_item in vehicle_serializer.data:
            vehicle_data.append([
                vehicle_data_item['vehicle_plate_number'],
                vehicle_data_item['vehicle_general_condition'],
                vehicle_data_item['vehicle_type'],
                vehicle_data_item['vehicle_model'],
                vehicle_data_item['vehicle_engine_number'],
                vehicle_data_item['vehicle_color']
            ])

        vehicle_table = Table(vehicle_data)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('TABLEWIDTH', (0, 0), (-1, -1), '100%'),
        ])

        vehicle_table.setStyle(style)
        elements.append(vehicle_table)

        # Build the PDF document
        pdf.build(elements)
        buffer.seek(0)

        # Send the PDF as a response
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="vehicle_details.pdf"'

        return response


@api_view(['GET'])
def generate_pdf(request):
    # Get current user (mechanic)
    mechanic = request.user
    mechanic_details = f"{mechanic.first_name} {mechanic.last_name}"

    # Fetch vehicle data
    vehicles = Vehicle.objects.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="vehicle_report.pdf"'

    # Create PDF
    p = canvas.Canvas(response, pagesize=letter)

    # Set up PDF content and styling
    p.setFont("Helvetica", 12)
    p.drawString(100, 750, "Vehicle Report")
    p.drawString(100, 730, f"Report generated on: {now()}")

    # Add mechanic details
    p.drawString(100, 700, "Mechanic Details:")
    p.drawString(120, 680, f"Name: {mechanic_details}")

    # Add vehicle information
    y_position = 650
    for vehicle in vehicles:
        # Display vehicle owner details
        vehicle_owner_details = f"Vehicle Owner: {vehicle.vehicle_owner.first_name} {vehicle.vehicle_owner.last_name}"
        p.drawString(100, y_position, vehicle_owner_details)

        # Display vehicle information
        vehicle_info = f"Plate Number: {vehicle.vehicle_plate_number}, Model: {vehicle.vehicle_model}, Type: {vehicle.vehicle_type}"
        p.drawString(120, y_position - 20, vehicle_info)

        # Display vehicle parts information (assuming VehiclePart model has a relevant field)
        # Replace vehicle_parts with the actual field in Vehicle model that points to VehiclePart
        vehicle_parts_info = f"Vehicle Parts: {vehicle.vehicle_parts}"
        p.drawString(140, y_position - 40, vehicle_parts_info)

        y_position -= 80  # Adjust vertical position for the next vehicle

    p.showPage()
    p.save()

    return response
