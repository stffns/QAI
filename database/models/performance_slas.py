"""
Performance SLAs Model - Enhanced with Hierarchy
===============================================

SQLModel para SLAs de performance con jerarquía de relevancia:
1. Endpoint + Country + Environment + App (más específico)
2. Country + Environment + App 
3. Environment + App
4. App General (menos específico)

Los SLAs más específicos tienen mayor prioridad en la aplicación.
"""

from datetime import datetime, time
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
from pydantic import validator, computed_field

class RiskLevel(str, Enum):
    """Niveles de riesgo para SLAs de performance"""
    LOW = "LOW"
    MEDIUM = "MEDIUM" 
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ValidationStatus(str, Enum):
    """Estados de validación de SLAs"""
    PENDING = "PENDING"
    VALID = "VALID"
    INVALID = "INVALID"
    EXPIRED = "EXPIRED"

class SLAScope(str, Enum):
    """Alcance/especificidad del SLA según jerarquía"""
    ENDPOINT_COUNTRY_ENV_APP = "ENDPOINT_COUNTRY_ENV_APP"  # Nivel 1: Más específico
    COUNTRY_ENV_APP = "COUNTRY_ENV_APP"                    # Nivel 2: Por país
    ENV_APP = "ENV_APP"                                    # Nivel 3: Por ambiente 
    APP_GENERAL = "APP_GENERAL"                           # Nivel 4: General

class PerformanceSLAs(SQLModel, table=True):
    """
    SLAs de Performance con Jerarquía de Relevancia
    
    Jerarquía (mayor a menor relevancia):
    1. Endpoint específico + País + Ambiente + App
    2. País + Ambiente + App (endpoint general)  
    3. Ambiente + App (país general)
    4. App general (ambiente y país generales)
    """
    
    # Primary key
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Core SLA definition (jerarquía de especificidad)
    app_name: str = Field(max_length=50, description="Nombre de la aplicación")
    environment: str = Field(max_length=50, description="Ambiente (prod, qa, staging, etc.)")
    country_code: Optional[str] = Field(default=None, max_length=3, description="Código de país (NULL o '*' = todos los países)")
    endpoint_pattern: Optional[str] = Field(default=None, max_length=200, description="Patrón de endpoint (NULL o '*' = todos los endpoints)")
    
    # Performance thresholds
    max_concurrent_users: int = Field(gt=0, description="Máximo número de usuarios concurrentes")
    max_duration_minutes: int = Field(gt=0, description="Duración máxima en minutos")
    max_rps: Optional[int] = Field(default=None, gt=0, description="Máximo requests por segundo")
    
    # Execution constraints
    execution_window_start: Optional[time] = Field(default=None, description="Hora de inicio permitida")
    execution_window_end: Optional[time] = Field(default=None, description="Hora de fin permitida")
    allowed_days: Optional[str] = Field(default=None, max_length=20, description="Días permitidos (ej: MON,TUE,WED)")
    timezone: str = Field(default="UTC", max_length=50, description="Zona horaria")
    
    # Risk and approval
    risk_level: RiskLevel = Field(description="Nivel de riesgo del SLA")
    requires_approval: bool = Field(default=False, description="Requiere aprobación manual")
    auto_approval_threshold: Optional[str] = Field(default=None, max_length=20, description="Umbral para auto-aprobación")
    
    # Notifications
    alert_on_violation: bool = Field(default=True, description="Alertar en violación de SLA")
    notification_channels: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON), description="Canales de notificación")
    
    # Hierarchy control (nuevos campos)
    specificity_level: int = Field(default=4, ge=1, le=4, description="Nivel de especificidad (1=más específico, 4=general)")
    hierarchy_priority: int = Field(default=1000, gt=0, description="Prioridad jerárquica (menor número = mayor prioridad)")
    sla_scope: SLAScope = Field(default=SLAScope.APP_GENERAL, description="Alcance del SLA según jerarquía")
    allows_cascade: bool = Field(default=True, description="Permite cascada a SLAs menos específicos")
    
    # Validation and audit
    validation_status: ValidationStatus = Field(default=ValidationStatus.PENDING, description="Estado de validación")
    last_validated_at: Optional[datetime] = Field(default=None, description="Última validación")
    description: Optional[str] = Field(default=None, description="Descripción del SLA")
    created_by: Optional[str] = Field(default=None, max_length=100, description="Usuario que creó el SLA")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    updated_at: Optional[datetime] = Field(default=None, description="Fecha de última actualización")
    is_active: bool = Field(default=True, description="SLA activo")
    
    @validator('country_code')
    def validate_country_code(cls, v):
        """Valida formato de código de país"""
        if v is None or v == '*':
            return v
        if not isinstance(v, str) or len(v) < 2 or len(v) > 3:
            raise ValueError("country_code debe tener 2-3 caracteres")
        return v.upper()
    
    @validator('execution_window_start', 'execution_window_end')
    def validate_execution_window(cls, v, values):
        """Valida que las ventanas de ejecución sean consistentes"""
        start = values.get('execution_window_start')
        end = values.get('execution_window_end')
        
        # Ambos deben ser None o ambos deben tener valor
        if (start is None) != (end is None):
            raise ValueError("execution_window_start y execution_window_end deben ser ambos None o ambos tener valor")
        
        return v
    
    @validator('max_rps')
    def validate_max_rps(cls, v):
        """Valida que max_rps sea positivo si se especifica"""
        if v is not None and v <= 0:
            raise ValueError("max_rps debe ser positivo")
        return v
    
    @computed_field
    @property
    def is_endpoint_specific(self) -> bool:
        """Indica si el SLA es específico para endpoints"""
        return (self.endpoint_pattern is not None and 
                self.endpoint_pattern != '*' and 
                self.endpoint_pattern != '')
    
    @computed_field
    @property
    def is_country_specific(self) -> bool:
        """Indica si el SLA es específico para un país"""
        return (self.country_code is not None and 
                self.country_code != '*' and 
                self.country_code != '')
    
    @computed_field
    @property
    def specificity_description(self) -> str:
        """Descripción del nivel de especificidad"""
        scope_descriptions = {
            SLAScope.ENDPOINT_COUNTRY_ENV_APP: "Endpoint específico + País + Ambiente + App",
            SLAScope.COUNTRY_ENV_APP: "País + Ambiente + App",
            SLAScope.ENV_APP: "Ambiente + App", 
            SLAScope.APP_GENERAL: "App general"
        }
        return scope_descriptions.get(self.sla_scope, "Desconocido")
    
    @computed_field
    @property
    def priority_label(self) -> str:
        """Etiqueta de prioridad basada en hierarchy_priority"""
        if self.hierarchy_priority <= 100:
            return "HIGHEST"
        elif self.hierarchy_priority <= 200:
            return "HIGH"
        elif self.hierarchy_priority <= 300:
            return "MEDIUM"
        else:
            return "LOW"
    
    @computed_field
    @property
    def coverage_pattern(self) -> str:
        """Patrón de cobertura del SLA"""
        parts = []
        parts.append(self.app_name)
        parts.append(self.environment)
        parts.append(self.country_code or "*")
        parts.append(self.endpoint_pattern or "*")
        return "/".join(parts)
    
    def matches_context(self, app: str, env: str, country: Optional[str] = None, endpoint: Optional[str] = None) -> bool:
        """
        Verifica si este SLA aplica al contexto dado
        
        Args:
            app: Nombre de la aplicación
            env: Ambiente
            country: Código de país (opcional)
            endpoint: Patrón de endpoint (opcional)
            
        Returns:
            True si el SLA aplica al contexto
        """
        # App y environment deben coincidir exactamente
        if self.app_name != app or self.environment != env:
            return False
        
        # Country: debe coincidir o ser general (None, '*')
        if self.is_country_specific:
            if not country or self.country_code != country.upper():
                return False
        
        # Endpoint: debe coincidir o ser general (None, '*')  
        if self.is_endpoint_specific:
            if not endpoint:
                return False
            # Aquí se podría implementar pattern matching más sofisticado
            if self.endpoint_pattern != endpoint:
                return False
        
        return True
    
    def calculate_hierarchy_values(self) -> None:
        """Calcula automáticamente los valores de jerarquía"""
        if self.is_endpoint_specific and self.is_country_specific:
            # Nivel 1: Endpoint + Country + Environment + App
            self.specificity_level = 1
            self.hierarchy_priority = 100
            self.sla_scope = SLAScope.ENDPOINT_COUNTRY_ENV_APP
        elif self.is_country_specific:
            # Nivel 2: Country + Environment + App
            self.specificity_level = 2
            self.hierarchy_priority = 200
            self.sla_scope = SLAScope.COUNTRY_ENV_APP
        elif not self.is_country_specific and not self.is_endpoint_specific:
            # Nivel 3: Environment + App
            self.specificity_level = 3
            self.hierarchy_priority = 300
            self.sla_scope = SLAScope.ENV_APP
        else:
            # Nivel 4: App General
            self.specificity_level = 4
            self.hierarchy_priority = 400
            self.sla_scope = SLAScope.APP_GENERAL
    
    @classmethod
    def create_endpoint_sla(
        cls,
        app_name: str,
        environment: str,
        country_code: str,
        endpoint_pattern: str,
        max_concurrent_users: int,
        max_duration_minutes: int,
        risk_level: RiskLevel,
        **kwargs
    ) -> "PerformanceSLAs":
        """Crea un SLA específico para endpoint (máxima prioridad)"""
        sla = cls(
            app_name=app_name,
            environment=environment,
            country_code=country_code,
            endpoint_pattern=endpoint_pattern,
            max_concurrent_users=max_concurrent_users,
            max_duration_minutes=max_duration_minutes,
            risk_level=risk_level,
            **kwargs
        )
        sla.calculate_hierarchy_values()
        return sla
    
    @classmethod
    def create_country_sla(
        cls,
        app_name: str,
        environment: str,
        country_code: str,
        max_concurrent_users: int,
        max_duration_minutes: int,
        risk_level: RiskLevel,
        **kwargs
    ) -> "PerformanceSLAs":
        """Crea un SLA específico para país"""
        sla = cls(
            app_name=app_name,
            environment=environment,
            country_code=country_code,
            endpoint_pattern=None,  # General para todos los endpoints
            max_concurrent_users=max_concurrent_users,
            max_duration_minutes=max_duration_minutes,
            risk_level=risk_level,
            **kwargs
        )
        sla.calculate_hierarchy_values()
        return sla
    
    @classmethod
    def create_environment_sla(
        cls,
        app_name: str,
        environment: str,
        max_concurrent_users: int,
        max_duration_minutes: int,
        risk_level: RiskLevel,
        **kwargs
    ) -> "PerformanceSLAs":
        """Crea un SLA específico para ambiente"""
        sla = cls(
            app_name=app_name,
            environment=environment,
            country_code=None,  # General para todos los países
            endpoint_pattern=None,  # General para todos los endpoints
            max_concurrent_users=max_concurrent_users,
            max_duration_minutes=max_duration_minutes,
            risk_level=risk_level,
            **kwargs
        )
        sla.calculate_hierarchy_values()
        return sla
    
    @classmethod
    def create_app_general_sla(
        cls,
        app_name: str,
        max_concurrent_users: int,
        max_duration_minutes: int,
        risk_level: RiskLevel,
        **kwargs
    ) -> "PerformanceSLAs":
        """Crea un SLA general para aplicación (menor prioridad)"""
        sla = cls(
            app_name=app_name,
            environment="*",  # Aplica a todos los ambientes
            country_code=None,
            endpoint_pattern=None,
            max_concurrent_users=max_concurrent_users,
            max_duration_minutes=max_duration_minutes,
            risk_level=risk_level,
            **kwargs
        )
        sla.calculate_hierarchy_values()
        return sla

    def __repr__(self) -> str:
        return f"<PerformanceSLA {self.coverage_pattern} [{self.sla_scope.value}] {self.risk_level.value}>"
