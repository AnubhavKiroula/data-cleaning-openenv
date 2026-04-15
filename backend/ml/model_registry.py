"""
Model Registry for DQN model management.

This module handles saving, loading, and versioning of trained DQN models
with metadata tracking and performance comparison.
"""
import os
import json
import torch
import shutil
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path
import glob
from dataclasses import dataclass, asdict
from .dqn_model import DQNAgent


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""
    version: str
    timestamp: str
    difficulty: str
    epochs: int
    final_reward: float
    best_reward: float
    training_time: float
    model_info: Dict[str, Any]
    file_path: str
    metrics_path: str
    file_size: int  # bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary."""
        return cls(**data)


class ModelRegistry:
    """
    Registry for managing trained DQN models.
    
    Handles model saving, loading, versioning, and performance tracking.
    """
    
    def __init__(self, registry_dir: str = "models"):
        """
        Initialize model registry.
        
        Args:
            registry_dir: Directory to store models
        """
        self.logger = logging.getLogger("ModelRegistry")
        
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(exist_ok=True)
        
        # Metadata file
        self.metadata_file = self.registry_dir / "registry.json"
        
        # Initialize metadata
        self.models: Dict[str, ModelMetadata] = {}
        self._load_metadata()
        
        self.logger.info(f"ModelRegistry initialized with directory: {registry_dir}")
    
    def _load_metadata(self) -> None:
        """Load model metadata from registry file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                
                for version, model_data in data.items():
                    self.models[version] = ModelMetadata.from_dict(model_data)
                
                self.logger.info(f"Loaded metadata for {len(self.models)} models")
            except Exception as e:
                self.logger.error(f"Error loading metadata: {e}")
                self.models = {}
        else:
            self.logger.info("No existing metadata file found")
    
    def _save_metadata(self) -> None:
        """Save model metadata to registry file."""
        try:
            data = {version: metadata.to_dict() for version, metadata in self.models.items()}
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug("Metadata saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving metadata: {e}")
    
    def register_model(self, agent: DQNAgent, version: str, difficulty: str, 
                      epochs: int, final_reward: float, best_reward: float,
                      training_time: float, training_metrics: Dict[str, Any]) -> str:
        """
        Register a new model in the registry.
        
        Args:
            agent: Trained DQN agent
            version: Model version string
            difficulty: Training difficulty
            epochs: Number of training epochs
            final_reward: Final average reward
            best_reward: Best reward achieved
            training_time: Training time in seconds
            training_metrics: Additional training metrics
            
        Returns:
            Path to saved model file
        """
        self.logger.info(f"Registering model: {version}")
        
        # Create model filename
        model_filename = f"dqn_{difficulty}_v{version}_epochs{epochs}_reward{final_reward:.3f}.pt"
        model_path = self.registry_dir / model_filename
        
        # Save model
        agent.save_model(str(model_path))
        
        # Save training metrics
        metrics_filename = model_filename.replace('.pt', '_metrics.json')
        metrics_path = self.registry_dir / metrics_filename
        with open(metrics_path, 'w') as f:
            json.dump(training_metrics, f, indent=2)
        
        # Get file size
        file_size = model_path.stat().st_size
        
        # Create metadata
        metadata = ModelMetadata(
            version=version,
            timestamp=datetime.now().isoformat(),
            difficulty=difficulty,
            epochs=epochs,
            final_reward=final_reward,
            best_reward=best_reward,
            training_time=training_time,
            model_info=agent.get_model_info(),
            file_path=str(model_path),
            metrics_path=str(metrics_path),
            file_size=file_size
        )
        
        # Register in metadata
        self.models[version] = metadata
        self._save_metadata()
        
        self.logger.info(f"Model registered: {version} at {model_path}")
        return str(model_path)
    
    def load_model(self, version: str, state_dim: int, action_dim: int, device: str = "cpu") -> DQNAgent:
        """
        Load a model from the registry.
        
        Args:
            version: Model version to load
            state_dim: State dimension for agent
            action_dim: Action dimension for agent
            device: PyTorch device
            
        Returns:
            Loaded DQN agent
            
        Raises:
            ValueError: If model version not found
        """
        if version not in self.models:
            raise ValueError(f"Model version {version} not found in registry")
        
        metadata = self.models[version]
        
        if not os.path.exists(metadata.file_path):
            raise FileNotFoundError(f"Model file not found: {metadata.file_path}")
        
        # Create agent
        agent = DQNAgent(state_dim, action_dim, device=device)
        
        # Load model
        agent.load_model(metadata.file_path)
        
        self.logger.info(f"Model loaded: {version}")
        return agent
    
    def get_best_model(self, metric: str = "final_reward", difficulty: Optional[str] = None) -> Optional[str]:
        """
        Get the best model version based on specified metric.
        
        Args:
            metric: Metric to compare ('final_reward', 'best_reward', 'epochs')
            difficulty: Filter by difficulty (optional)
            
        Returns:
            Best model version or None
        """
        filtered_models = self.models.values()
        
        # Filter by difficulty if specified
        if difficulty:
            filtered_models = [m for m in filtered_models if m.difficulty == difficulty]
        
        if not filtered_models:
            return None
        
        # Find best model based on metric
        if metric == "final_reward":
            best_model = max(filtered_models, key=lambda m: m.final_reward)
        elif metric == "best_reward":
            best_model = max(filtered_models, key=lambda m: m.best_reward)
        elif metric == "epochs":
            best_model = min(filtered_models, key=lambda m: m.epochs)  # Fewest epochs
        else:
            raise ValueError(f"Unknown metric: {metric}")
        
        return best_model.version
    
    def list_models(self, difficulty: Optional[str] = None, sort_by: str = "timestamp") -> List[Dict[str, Any]]:
        """
        List all models in the registry.
        
        Args:
            difficulty: Filter by difficulty (optional)
            sort_by: Sort key ('timestamp', 'final_reward', 'best_reward', 'epochs')
            
        Returns:
            List of model information dictionaries
        """
        models = list(self.models.values())
        
        # Filter by difficulty
        if difficulty:
            models = [m for m in models if m.difficulty == difficulty]
        
        # Sort models
        reverse_order = sort_by in ["final_reward", "best_reward"]  # Higher is better
        models.sort(key=lambda m: getattr(m, sort_by), reverse=reverse_order)
        
        # Convert to dictionaries
        return [m.to_dict() for m in models]
    
    def delete_model(self, version: str) -> bool:
        """
        Delete a model from the registry.
        
        Args:
            version: Model version to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if version not in self.models:
            self.logger.warning(f"Model version {version} not found")
            return False
        
        metadata = self.models[version]
        
        try:
            # Delete model file
            if os.path.exists(metadata.file_path):
                os.remove(metadata.file_path)
            
            # Delete metrics file
            if os.path.exists(metadata.metrics_path):
                os.remove(metadata.metrics_path)
            
            # Remove from registry
            del self.models[version]
            self._save_metadata()
            
            self.logger.info(f"Model deleted: {version}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting model {version}: {e}")
            return False
    
    def export_model(self, version: str, export_path: str) -> bool:
        """
        Export a model to a specified path.
        
        Args:
            version: Model version to export
            export_path: Export destination path
            
        Returns:
            True if exported successfully, False otherwise
        """
        if version not in self.models:
            self.logger.warning(f"Model version {version} not found")
            return False
        
        metadata = self.models[version]
        
        try:
            # Create export directory
            os.makedirs(export_path, exist_ok=True)
            
            # Copy model file
            model_filename = os.path.basename(metadata.file_path)
            export_model_path = os.path.join(export_path, model_filename)
            shutil.copy2(metadata.file_path, export_model_path)
            
            # Copy metrics file
            metrics_filename = os.path.basename(metadata.metrics_path)
            export_metrics_path = os.path.join(export_path, metrics_filename)
            shutil.copy2(metadata.metrics_path, export_metrics_path)
            
            # Export metadata
            export_metadata_path = os.path.join(export_path, f"{version}_metadata.json")
            with open(export_metadata_path, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
            
            self.logger.info(f"Model exported: {version} to {export_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting model {version}: {e}")
            return False
    
    def import_model(self, import_path: str, version: str) -> bool:
        """
        Import a model from a specified path.
        
        Args:
            import_path: Path containing model files
            version: Version to assign to imported model
            
        Returns:
            True if imported successfully, False otherwise
        """
        try:
            # Find model files
            model_files = glob.glob(os.path.join(import_path, "*.pt"))
            metadata_files = glob.glob(os.path.join(import_path, "*_metadata.json"))
            
            if not model_files:
                self.logger.error(f"No model files found in {import_path}")
                return False
            
            # Copy model files
            for model_file in model_files:
                dest_path = self.registry_dir / os.path.basename(model_file)
                shutil.copy2(model_file, dest_path)
            
            # Copy metadata files
            for metadata_file in metadata_files:
                dest_path = self.registry_dir / os.path.basename(metadata_file)
                shutil.copy2(metadata_file, dest_path)
            
            # Load and register metadata
            metadata_file = os.path.join(import_path, f"{version}_metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata_dict = json.load(f)
                
                metadata = ModelMetadata.from_dict(metadata_dict)
                metadata.version = version  # Update version
                metadata.file_path = str(self.registry_dir / os.path.basename(metadata.file_path))
                metadata.metrics_path = str(self.registry_dir / os.path.basename(metadata.metrics_path))
                
                self.models[version] = metadata
                self._save_metadata()
            
            self.logger.info(f"Model imported: {version} from {import_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing model {version}: {e}")
            return False
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Registry statistics dictionary
        """
        if not self.models:
            return {
                "total_models": 0,
                "total_size": 0,
                "difficulties": [],
                "best_model": None
            }
        
        # Calculate statistics
        total_size = sum(m.file_size for m in self.models.values())
        difficulties = list(set(m.difficulty for m in self.models.values()))
        
        # Find best model
        best_model = self.get_best_model("final_reward")
        
        return {
            "total_models": len(self.models),
            "total_size": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "difficulties": difficulties,
            "best_model": best_model,
            "oldest_model": min(self.models.values(), key=lambda m: m.timestamp).version,
            "newest_model": max(self.models.values(), key=lambda m: m.timestamp).version
        }
    
    def cleanup_old_models(self, keep_count: int = 5) -> int:
        """
        Clean up old models, keeping only the best N models.
        
        Args:
            keep_count: Number of models to keep per difficulty
            
        Returns:
            Number of models deleted
        """
        deleted_count = 0
        
        # Group models by difficulty
        difficulty_groups = {}
        for version, metadata in self.models.items():
            if metadata.difficulty not in difficulty_groups:
                difficulty_groups[metadata.difficulty] = []
            difficulty_groups[metadata.difficulty].append((version, metadata))
        
        # Keep best N models per difficulty
        for difficulty, models in difficulty_groups.items():
            # Sort by final reward (best first)
            models.sort(key=lambda x: x[1].final_reward, reverse=True)
            
            # Delete models beyond keep_count
            for version, metadata in models[keep_count:]:
                if self.delete_model(version):
                    deleted_count += 1
        
        self.logger.info(f"Cleaned up {deleted_count} old models")
        return deleted_count
    
    def validate_models(self) -> Dict[str, List[str]]:
        """
        Validate all models in the registry.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": [],
            "invalid": [],
            "missing_files": []
        }
        
        for version, metadata in self.models.items():
            # Check if model file exists
            if not os.path.exists(metadata.file_path):
                results["missing_files"].append(version)
                results["invalid"].append(version)
                continue
            
            # Try to load model (basic validation)
            try:
                # Just check if file can be loaded as PyTorch checkpoint
                torch.load(metadata.file_path, map_location='cpu')
                results["valid"].append(version)
            except Exception as e:
                self.logger.warning(f"Model {version} validation failed: {e}")
                results["invalid"].append(version)
        
        return results


# Convenience functions for common operations
def save_model(agent: DQNAgent, version: str, difficulty: str, epochs: int,
              final_reward: float, best_reward: float, training_time: float,
              training_metrics: Dict[str, Any], registry_dir: str = "models") -> str:
    """
    Convenience function to save a model.
    
    Returns:
        Model file path
    """
    registry = ModelRegistry(registry_dir)
    return registry.register_model(
        agent, version, difficulty, epochs, final_reward, best_reward,
        training_time, training_metrics
    )


def load_model(version: str, state_dim: int, action_dim: int, 
              device: str = "cpu", registry_dir: str = "models") -> DQNAgent:
    """
    Convenience function to load a model.
    
    Returns:
        Loaded DQN agent
    """
    registry = ModelRegistry(registry_dir)
    return registry.load_model(version, state_dim, action_dim, device)


def get_best_model(metric: str = "final_reward", difficulty: Optional[str] = None,
                  registry_dir: str = "models") -> Optional[str]:
    """
    Convenience function to get best model version.
    
    Returns:
        Best model version or None
    """
    registry = ModelRegistry(registry_dir)
    return registry.get_best_model(metric, difficulty)
