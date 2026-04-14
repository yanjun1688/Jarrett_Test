"""
Project Models

This module contains project-related data models.
"""

from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """Project model"""
    
    name = models.CharField(max_length=100, verbose_name='Project Name')
    description = models.TextField(blank=True, verbose_name='Project Description')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='core_projects',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    
    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-created_at']
        db_table = 'core_project'
    
    def __str__(self) -> str:
        return self.name


class Module(models.Model):
    """Module model"""
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='modules',
        verbose_name='Project'
    )
    name = models.CharField(max_length=100, verbose_name='Module Name')
    description = models.TextField(blank=True, verbose_name='Module Description')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='core_modules',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'
        ordering = ['name']
        unique_together = ['project', 'name']
        db_table = 'core_module'
    
    def __str__(self) -> str:
        return f"{self.project.name} - {self.name}"