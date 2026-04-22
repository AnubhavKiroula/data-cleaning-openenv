"""
Synthetic dataset generator for DQN training.

This module creates synthetic dirty datasets with known patterns
for training the DQN agent on data cleaning tasks.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
import random
import logging
from dataclasses import dataclass
from enum import Enum


class DifficultyLevel(Enum):
    """Difficulty levels for synthetic datasets."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class DatasetConfig:
    """Configuration for synthetic dataset generation."""
    num_rows: int = 1000
    difficulty: DifficultyLevel = DifficultyLevel.EASY
    seed: Optional[int] = None
    
    # Error rates
    missing_rate: float = 0.0
    duplicate_rate: float = 0.0
    outlier_rate: float = 0.0
    category_error_rate: float = 0.0
    type_error_rate: float = 0.0
    formatting_error_rate: float = 0.0


class SyntheticDatasetGenerator:
    """
    Generates synthetic datasets with controlled data quality issues.
    
    Creates clean base data and injects specific types of errors
    with known ground truth for training evaluation.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.logger = logging.getLogger("SyntheticDatasetGenerator")
        
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        # Define clean data distributions
        self.name_options = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank"]
        self.dept_options = ["engineering", "sales", "marketing", "hr", "finance"]
        self.email_domains = ["gmail.com", "yahoo.com", "company.com", "outlook.com"]
        
        self.logger.info(f"SyntheticDatasetGenerator initialized with seed: {seed}")
    
    def get_config_for_difficulty(self, difficulty: DifficultyLevel) -> DatasetConfig:
        """
        Get predefined configuration for difficulty level.
        
        Args:
            difficulty: Difficulty level
            
        Returns:
            Dataset configuration
        """
        if difficulty == DifficultyLevel.EASY:
            return DatasetConfig(
                difficulty=difficulty,
                missing_rate=0.2,
                type_error_rate=0.05,
                duplicate_rate=0.0,
                outlier_rate=0.0,
                category_error_rate=0.0,
                formatting_error_rate=0.0
            )
        elif difficulty == DifficultyLevel.MEDIUM:
            return DatasetConfig(
                difficulty=difficulty,
                missing_rate=0.3,
                duplicate_rate=0.15,
                type_error_rate=0.05,
                outlier_rate=0.0,
                category_error_rate=0.0,
                formatting_error_rate=0.05
            )
        elif difficulty == DifficultyLevel.HARD:
            return DatasetConfig(
                difficulty=difficulty,
                missing_rate=0.3,
                duplicate_rate=0.15,
                outlier_rate=0.1,
                category_error_rate=0.2,
                type_error_rate=0.05,
                formatting_error_rate=0.1
            )
        else:
            raise ValueError(f"Unknown difficulty level: {difficulty}")
    
    def generate_clean_dataset(self, num_rows: int) -> pd.DataFrame:
        """
        Generate clean base dataset.
        
        Args:
            num_rows: Number of rows to generate
            
        Returns:
            Clean DataFrame
        """
        data = []
        
        for i in range(num_rows):
            # Generate realistic data
            name = random.choice(self.name_options)
            dept = random.choice(self.dept_options)
            age = np.random.normal(35, 10)  # Age around 35 with std 10
            age = max(18, min(70, int(age)))  # Clamp to reasonable range
            
            salary = self._generate_salary_for_dept(dept)
            score = np.random.normal(75, 15)  # Score around 75 with std 15
            score = max(0, min(100, int(score)))  # Clamp to 0-100
            
            email = f"{name.lower()}.{random.randint(1, 99)}@{random.choice(self.email_domains)}"
            
            data.append({
                'id': i + 1,
                'name': name,
                'age': age,
                'salary': salary,
                'score': score,
                'dept': dept,
                'email': email
            })
        
        df = pd.DataFrame(data)
        self.logger.info(f"Generated clean dataset with {len(df)} rows")
        
        return df
    
    def _generate_salary_for_dept(self, dept: str) -> int:
        """Generate realistic salary based on department."""
        salary_ranges = {
            'engineering': (60000, 150000),
            'sales': (40000, 120000),
            'marketing': (50000, 110000),
            'hr': (45000, 90000),
            'finance': (55000, 130000)
        }
        
        min_sal, max_sal = salary_ranges.get(dept, (40000, 100000))
        return int(np.random.uniform(min_sal, max_sal))
    
    def inject_missing_values(self, df: pd.DataFrame, missing_rate: float) -> Tuple[pd.DataFrame, List[str]]:
        """
        Inject missing values into dataset.
        
        Args:
            df: Clean DataFrame
            missing_rate: Proportion of values to make missing
            
        Returns:
            Tuple of (dirty DataFrame, list of missing issues)
        """
        df_dirty = df.copy()
        issues = []
        
        # Columns that can have missing values
        nullable_columns = ['age', 'salary', 'score', 'name', 'email']
        
        for col in nullable_columns:
            if col in df_dirty.columns:
                # Randomly select rows to make missing
                n_missing = int(len(df_dirty) * missing_rate * 0.5)  # Distribute across columns
                missing_indices = np.random.choice(len(df_dirty), n_missing, replace=False)
                
                for idx in missing_indices:
                    df_dirty.loc[idx, col] = None
                    issues.append(f"missing:{col}")
        
        self.logger.info(f"Injected {len(issues)} missing values")
        return df_dirty, issues
    
    def inject_duplicates(self, df: pd.DataFrame, duplicate_rate: float) -> Tuple[pd.DataFrame, List[str]]:
        """
        Inject duplicate rows into dataset.
        
        Args:
            df: Clean DataFrame
            duplicate_rate: Proportion of rows to duplicate
            
        Returns:
            Tuple of (dirty DataFrame, list of duplicate issues)
        """
        df_dirty = df.copy()
        issues = []
        
        n_duplicates = int(len(df_dirty) * duplicate_rate)
        
        for _ in range(n_duplicates):
            # Select a random row to duplicate
            original_idx = np.random.choice(len(df_dirty))
            original_row = df_dirty.iloc[original_idx].copy()
            
            # Add small variations to make it fuzzy
            if 'name' in original_row and random.random() < 0.3:
                original_row['name'] = original_row['name'].lower()
            
            # Append as new row
            df_dirty = pd.concat([df_dirty, original_row.to_frame().T], ignore_index=True)
            issues.append("duplicate:row")
        
        self.logger.info(f"Injected {n_duplicates} duplicate rows")
        return df_dirty, issues
    
    def inject_outliers(self, df: pd.DataFrame, outlier_rate: float) -> Tuple[pd.DataFrame, List[str]]:
        """
        Inject outlier values into dataset.
        
        Args:
            df: Clean DataFrame
            outlier_rate: Proportion of values to make outliers
            
        Returns:
            Tuple of (dirty DataFrame, list of outlier issues)
        """
        df_dirty = df.copy()
        issues = []
        
        numeric_columns = ['age', 'salary', 'score']
        
        for col in numeric_columns:
            if col in df_dirty.columns:
                n_outliers = int(len(df_dirty) * outlier_rate * 0.3)  # Distribute across columns
                outlier_indices = np.random.choice(len(df_dirty), n_outliers, replace=False)
                
                for idx in outlier_indices:
                    original_val = df_dirty.loc[idx, col]
                    
                    if col == 'age':
                        # Extreme ages
                        outlier_val = random.choice([5, 95, 120])
                    elif col == 'salary':
                        # Extreme salaries
                        outlier_val = random.choice([15000, 500000])
                    elif col == 'score':
                        # Extreme scores
                        outlier_val = random.choice([-10, 150])
                    else:
                        continue
                    
                    df_dirty.loc[idx, col] = outlier_val
                    issues.append(f"outlier:{col}")
        
        self.logger.info(f"Injected {len(issues)} outliers")
        return df_dirty, issues
    
    def inject_category_errors(self, df: pd.DataFrame, error_rate: float) -> Tuple[pd.DataFrame, List[str]]:
        """
        Inject categorical inconsistencies into dataset.
        
        Args:
            df: Clean DataFrame
            error_rate: Proportion of categorical values to corrupt
            
        Returns:
            Tuple of (dirty DataFrame, list of category issues)
        """
        df_dirty = df.copy()
        issues = []
        
        categorical_columns = ['dept', 'name']
        
        for col in categorical_columns:
            if col in df_dirty.columns:
                n_errors = int(len(df_dirty) * error_rate * 0.5)
                error_indices = np.random.choice(len(df_dirty), n_errors, replace=False)
                
                for idx in error_indices:
                    original_val = df_dirty.loc[idx, col]
                    
                    if col == 'dept':
                        # Typos in department names
                        typos = {
                            'engineering': 'enginering',
                            'sales': 'salse',
                            'marketing': 'marketting',
                            'hr': 'h.r',
                            'finance': 'financ'
                        }
                        df_dirty.loc[idx, col] = typos.get(original_val, original_val + 'x')
                        issues.append(f"category:{col}")
                    elif col == 'name':
                        # Case variations
                        if random.random() < 0.5:
                            df_dirty.loc[idx, col] = original_val.upper()
                        else:
                            df_dirty.loc[idx, col] = original_val.lower()
                        issues.append(f"category:{col}")
        
        self.logger.info(f"Injected {len(issues)} category errors")
        return df_dirty, issues
    
    def inject_type_errors(self, df: pd.DataFrame, error_rate: float) -> Tuple[pd.DataFrame, List[str]]:
        """
        Inject type errors into dataset.
        
        Args:
            df: Clean DataFrame
            error_rate: Proportion of values to corrupt with type errors
            
        Returns:
            Tuple of (dirty DataFrame, list of type issues)
        """
        df_dirty = df.copy()
        issues = []
        
        # Focus on score column (should be numeric)
        if 'score' in df_dirty.columns:
            n_errors = int(len(df_dirty) * error_rate)
            error_indices = np.random.choice(len(df_dirty), n_errors, replace=False)
            
            for idx in error_indices:
                # Convert numeric score to string
                original_val = df_dirty.loc[idx, 'score']
                df_dirty.loc[idx, 'score'] = f"{original_val} points"
                issues.append("wrong_type:score")
        
        self.logger.info(f"Injected {len(issues)} type errors")
        return df_dirty, issues
    
    def inject_formatting_errors(self, df: pd.DataFrame, error_rate: float) -> Tuple[pd.DataFrame, List[str]]:
        """
        Inject formatting errors into dataset.
        
        Args:
            df: Clean DataFrame
            error_rate: Proportion of values to corrupt with formatting errors
            
        Returns:
            Tuple of (dirty DataFrame, list of formatting issues)
        """
        df_dirty = df.copy()
        issues = []
        
        # Focus on email and name columns
        formatting_columns = ['email', 'name']
        
        for col in formatting_columns:
            if col in df_dirty.columns:
                n_errors = int(len(df_dirty) * error_rate * 0.5)
                error_indices = np.random.choice(len(df_dirty), n_errors, replace=False)
                
                for idx in error_indices:
                    original_val = df_dirty.loc[idx, col]
                    
                    if col == 'email':
                        # Remove @ or add extra characters
                        if '@' in original_val:
                            if random.random() < 0.5:
                                df_dirty.loc[idx, col] = original_val.replace('@', ' at ')
                            else:
                                df_dirty.loc[idx, col] = original_val + '.com'
                        issues.append(f"formatting:{col}")
                    elif col == 'name':
                        # Add extra spaces or special characters
                        if random.random() < 0.5:
                            df_dirty.loc[idx, col] = original_val + ' '
                        else:
                            df_dirty.loc[idx, col] = original_val.replace(' ', '_')
                        issues.append(f"formatting:{col}")
        
        self.logger.info(f"Injected {len(issues)} formatting errors")
        return df_dirty, issues
    
    def generate_dirty_dataset(self, config: DatasetConfig) -> Tuple[pd.DataFrame, List[str]]:
        """
        Generate complete dirty dataset with all error types.
        
        Args:
            config: Dataset configuration
            
        Returns:
            Tuple of (dirty DataFrame, list of all issues)
        """
        # Generate clean base data
        df_clean = self.generate_clean_dataset(config.num_rows)
        
        # Inject errors progressively
        df_dirty = df_clean.copy()
        all_issues = []
        
        # Missing values
        if config.missing_rate > 0:
            df_dirty, issues = self.inject_missing_values(df_dirty, config.missing_rate)
            all_issues.extend(issues)
        
        # Duplicates
        if config.duplicate_rate > 0:
            df_dirty, issues = self.inject_duplicates(df_dirty, config.duplicate_rate)
            all_issues.extend(issues)
        
        # Outliers
        if config.outlier_rate > 0:
            df_dirty, issues = self.inject_outliers(df_dirty, config.outlier_rate)
            all_issues.extend(issues)
        
        # Category errors
        if config.category_error_rate > 0:
            df_dirty, issues = self.inject_category_errors(df_dirty, config.category_error_rate)
            all_issues.extend(issues)
        
        # Type errors
        if config.type_error_rate > 0:
            df_dirty, issues = self.inject_type_errors(df_dirty, config.type_error_rate)
            all_issues.extend(issues)
        
        # Formatting errors
        if config.formatting_error_rate > 0:
            df_dirty, issues = self.inject_formatting_errors(df_dirty, config.formatting_error_rate)
            all_issues.extend(issues)
        
        # Shuffle rows to mix issues
        df_dirty = df_dirty.sample(frac=1).reset_index(drop=True)
        
        self.logger.info(f"Generated dirty dataset: {len(df_dirty)} rows, {len(all_issues)} total issues")
        
        return df_dirty, all_issues
    
    def create_training_episodes(self, config: DatasetConfig, num_episodes: int = 100) -> List[Dict[str, Any]]:
        """
        Create training episodes from synthetic data.
        
        Args:
            config: Dataset configuration
            num_episodes: Number of episodes to create
            
        Returns:
            List of episode dictionaries
        """
        episodes = []
        
        for episode_id in range(num_episodes):
            # Generate dirty dataset
            df_dirty, issues = self.generate_dirty_dataset(config)
            
            # Create episode with row-by-row observations
            episode = {
                'episode_id': episode_id,
                'config': config,
                'dataset': df_dirty,
                'issues': issues,
                'rows': []
            }
            
            # Create observations for each row
            for idx, row in df_dirty.iterrows():
                # Detect issues for this specific row
                row_issues = self._detect_row_issues(row, issues)
                
                observation = {
                    'row_index': idx,
                    'current_data': row.to_dict(),
                    'issues_detected': row_issues,
                    'legal_actions': ['skip', 'fill_missing', 'remove_duplicate', 
                                    'remove_outlier', 'fix_category', 'fix_type', 'fix_formatting']
                }
                
                episode['rows'].append(observation)
            
            episodes.append(episode)
        
        self.logger.info(f"Created {len(episodes)} training episodes")
        return episodes
    
    def _detect_row_issues(self, row: pd.Series, all_issues: List[str]) -> List[str]:
        """
        Detect issues specific to this row.
        
        Args:
            row: Row data
            all_issues: All issues in dataset
            
        Returns:
            List of issues for this row
        """
        row_issues = []
        
        # Check for missing values
        for col in ['age', 'salary', 'score', 'name', 'email']:
            if col in row and pd.isna(row[col]):
                row_issues.append(f"missing:{col}")
        
        # Check for type errors
        if 'score' in row and isinstance(row['score'], str):
            row_issues.append("wrong_type:score")
        
        # Check for formatting issues
        if 'email' in row and isinstance(row['email'], str):
            if '@' not in row['email'] or ' at ' in row['email']:
                row_issues.append("formatting:email")
        
        if 'name' in row and isinstance(row['name'], str):
            if '  ' in row['name'] or '_' in row['name']:
                row_issues.append("formatting:name")
        
        # Check for category issues
        if 'dept' in row and isinstance(row['dept'], str):
            if row['dept'] not in self.dept_options:
                row_issues.append("category:dept")
        
        # Simplified duplicate/outlier detection (would be more complex in practice)
        # For training, we'll use a simplified approach
        
        return row_issues
    
    def save_dataset(self, df: pd.DataFrame, filepath: str) -> None:
        """
        Save dataset to CSV file.
        
        Args:
            df: DataFrame to save
            filepath: Output file path
        """
        df.to_csv(filepath, index=False)
        self.logger.info(f"Dataset saved to {filepath}")
    
    def load_dataset(self, filepath: str) -> pd.DataFrame:
        """
        Load dataset from CSV file.
        
        Args:
            filepath: Input file path
            
        Returns:
            Loaded DataFrame
        """
        df = pd.read_csv(filepath)
        self.logger.info(f"Dataset loaded from {filepath}")
        return df
