"""机器学习API

提供模型管理、性能监控、在线学习等接口。
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from vnpy_china_monitor.web.models.response import ApiResponse

logger = logging.getLogger(__name__)

# 创建路由器
ml_router = APIRouter(
    prefix="/api/ml",
    tags=["机器学习"],
)


# ==================== 请求模型 ====================

class ModelPerformanceRequest(BaseModel):
    """模型性能请求"""
    model_id: str


class OnlineLearningConfigRequest(BaseModel):
    """在线学习配置请求"""
    model_id: str
    min_samples: Optional[int] = 100
    max_samples: Optional[int] = 10000
    update_interval: Optional[int] = 100
    learning_rate: Optional[float] = 0.01
    enable_auto_retrain: Optional[bool] = True


class TrainingSampleRequest(BaseModel):
    """训练样本请求"""
    model_id: str
    features: List[float]
    label: float
    weight: Optional[float] = 1.0


# ==================== API 端点 ====================

# 全局服务实例（实际应用中应该从应用状态中获取）
_ml_monitor_service = None
_online_learning_service = None


def get_ml_monitor_service(request: Request):
    """获取ML监控服务实例（优先 app.state，回退全局变量）"""
    service = getattr(request.app.state, "ml_monitor_service", None) or _ml_monitor_service
    if service is None:
        raise HTTPException(status_code=503, detail="ML监控服务未初始化")
    return service


def get_online_learning_service(request: Request):
    """获取在线学习服务实例（优先 app.state，回退全局变量）"""
    service = getattr(request.app.state, "online_learning_service", None) or _online_learning_service
    if service is None:
        raise HTTPException(status_code=503, detail="在线学习服务未初始化")
    return service


@ml_router.get("/models", response_model=ApiResponse)
async def get_models(
    service=Depends(get_ml_monitor_service)
) -> ApiResponse:
    """获取所有模型列表

    Returns:
        API响应
    """
    try:
        model_ids = service.get_all_model_ids()
        models = []

        for model_id in model_ids:
            info = service.get_model_info(model_id)
            models.append({
                "model_id": model_id,
                "name": info.get("model_name", model_id),
                "type": info.get("model_type", "unknown"),
                "is_trained": info.get("is_trained", False),
            })

        return ApiResponse(
            success=True,
            data={"models": models, "count": len(models)}
        )
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/models/{model_id}/performance", response_model=ApiResponse)
async def get_model_performance(
    model_id: str,
    service=Depends(get_ml_monitor_service)
) -> ApiResponse:
    """获取模型性能

    Args:
        model_id: 模型ID

    Returns:
        API响应
    """
    try:
        report = service.generate_performance_report(model_id)
        return ApiResponse(
            success=True,
            data=report
        )
    except Exception as e:
        logger.error(f"获取模型性能失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/models/{model_id}/performance/trend", response_model=ApiResponse)
async def get_model_performance_trend(
    model_id: str,
    metric: str = Query("direction_accuracy", description="性能指标"),
    window: int = Query(10, description="趋势窗口大小"),
    service=Depends(get_ml_monitor_service)
) -> ApiResponse:
    """获取模型性能趋势

    Args:
        model_id: 模型ID
        metric: 性能指标
        window: 窗口大小

    Returns:
        API响应
    """
    try:
        from ..monitoring import PerformanceMetric

        metric_enum = PerformanceMetric(metric)
        trend = service.get_performance_trend(model_id, metric_enum, window)

        if trend is None:
            return ApiResponse(
                success=True,
                data={"trend": [], "message": "暂无趋势数据"}
            )

        return ApiResponse(
            success=True,
            data={
                "model_id": model_id,
                "metric": metric,
                "trend": trend.tolist(),
                "window": window
            }
        )
    except Exception as e:
        logger.error(f"获取性能趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/performance/check", response_model=ApiResponse)
async def check_all_models_performance(
    service=Depends(get_ml_monitor_service)
) -> ApiResponse:
    """检查所有模型性能

    Returns:
        API响应
    """
    try:
        performance_results = service.check_all_models()
        return ApiResponse(
            success=True,
            data={
                "results": performance_results,
                "checked_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"检查模型性能失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/decay/detect", response_model=ApiResponse)
async def detect_performance_decay(
    model_id: str = Query(None, description="模型ID，为空则检查所有"),
    metric: str = Query("direction_accuracy", description="检测指标"),
    threshold: float = Query(0.1, description="衰减阈值"),
    service=Depends(get_ml_monitor_service)
) -> ApiResponse:
    """检测模型性能衰减

    Args:
        model_id: 模型ID
        metric: 检测指标
        threshold: 衰减阈值

    Returns:
        API响应
    """
    try:
        from ..monitoring import PerformanceMetric

        metric_enum = PerformanceMetric(metric)

        if model_id:
            results = {model_id: service.detect_performance_decay(model_id, metric_enum, threshold)}
        else:
            model_ids = service.get_all_model_ids()
            results = {}
            for mid in model_ids:
                results[mid] = service.detect_performance_decay(mid, metric_enum, threshold)

        return ApiResponse(
            success=True,
            data={
                "results": results,
                "metric": metric,
                "threshold": threshold
            }
        )
    except Exception as e:
        logger.error(f"检测性能衰减失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 在线学习 API ====================

@ml_router.post("/online/register", response_model=ApiResponse)
async def register_online_learning(
    request: OnlineLearningConfigRequest,
    service=Depends(get_online_learning_service)
) -> ApiResponse:
    """注册模型在线学习

    Args:
        request: 在线学习配置请求

    Returns:
        API响应
    """
    try:
        from ..online_learning import OnlineLearningConfig

        config = OnlineLearningConfig(
            min_samples=request.min_samples,
            max_samples=request.max_samples,
            update_interval=request.update_interval,
            learning_rate=request.learning_rate,
            enable_auto_retrain=request.enable_auto_retrain
        )

        success = service.register_model(request.model_id, config)

        return ApiResponse(
            success=success,
            message=f"{'注册成功' if success else '注册失败'}: {request.model_id}"
        )
    except Exception as e:
        logger.error(f"注册在线学习失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/online/samples", response_model=ApiResponse)
async def add_training_samples(
    request: TrainingSampleRequest,
    service=Depends(get_online_learning_service)
) -> ApiResponse:
    """添加训练样本

    Args:
        request: 训练样本请求

    Returns:
        API响应
    """
    try:
        import numpy as np

        features = np.array(request.features)
        service.add_sample(
            request.model_id,
            features,
            request.label,
            weight=request.weight
        )

        return ApiResponse(
            success=True,
            message="样本添加成功"
        )
    except Exception as e:
        logger.error(f"添加训练样本失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/online/update", response_model=ApiResponse)
async def update_models(
    model_id: Optional[str] = None,
    service=Depends(get_online_learning_service)
) -> ApiResponse:
    """检查并更新模型

    Args:
        model_id: 模型ID，为空则更新所有模型

    Returns:
        API响应
    """
    try:
        results = service.check_and_update(model_id)

        return ApiResponse(
            success=True,
            data={
                "results": results,
                "updated_models": list(results.keys()),
                "updated_count": len(results)
            }
        )
    except Exception as e:
        logger.error(f"更新模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.get("/online/info", response_model=ApiResponse)
async def get_online_learning_info(
    model_id: Optional[str] = None,
    service=Depends(get_online_learning_service)
) -> ApiResponse:
    """获取在线学习信息

    Args:
        model_id: 模型ID，为空则返回所有

    Returns:
        API响应
    """
    try:
        if model_id:
            info = service.get_learner_info(model_id)
            if info is None:
                raise HTTPException(status_code=404, detail=f"模型不存在: {model_id}")
            return ApiResponse(success=True, data=info)
        else:
            all_info = service.get_all_learner_info()
            return ApiResponse(
                success=True,
                data={
                    "learners": all_info,
                    "count": len(all_info)
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取在线学习信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@ml_router.post("/online/record", response_model=ApiResponse)
async def record_prediction_result(
    model_id: str,
    predicted_return: float,
    actual_return: float,
    service=Depends(get_online_learning_service)
) -> ApiResponse:
    """记录预测结果（用于在线学习）

    Args:
        model_id: 模型ID
        predicted_return: 预测收益率
        actual_return: 实际收益率

    Returns:
        API响应
    """
    try:
        service.record_prediction_result(
            model_id,
            predicted_return,
            actual_return
        )

        return ApiResponse(
            success=True,
            message="预测结果记录成功"
        )
    except Exception as e:
        logger.error(f"记录预测结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 辅助函数 ====================

def init_ml_api(monitor_service, online_learning_service):
    """初始化ML API服务

    Args:
        monitor_service: ML监控服务实例
        online_learning_service: 在线学习服务实例
    """
    global _ml_monitor_service, _online_learning_service
    _ml_monitor_service = monitor_service
    _online_learning_service = online_learning_service
    logger.info("ML API 服务已初始化")


__all__ = ["ml_router", "init_ml_api"]
