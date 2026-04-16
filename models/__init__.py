from importlib import import_module


class _LazyModelRegistry(dict):
    def __getitem__(self, key):
        if key not in self:
            raise KeyError(f"Model '{key}' is not registered.")

        value = super().__getitem__(key)
        if isinstance(value, tuple):
            module_name, class_name = value
            try:
                module = import_module(f".{module_name}", __name__)
                model_cls = getattr(module, class_name)
            except Exception as exc:
                raise ImportError(
                    f"Unable to load model '{key}'. Install its optional dependencies and retry."
                ) from exc

            self[key] = model_cls
            return model_cls

        return value


MODELS = _LazyModelRegistry({
    'random_forest': ('random_forest', 'RandomForest'),
    'sarimax': ('sarimax', 'Sarimax'),
    'orbit': ('orbit', 'Orbit'),
    'lstm': ('LSTM', 'MyLSTM'),
    'gru': ('GRU', 'MyGRU'),
    'arima': ('arima', 'MyARIMA'),
    'prophet': ('prophet', 'MyProphet'),
    'xgboost': ('xgboost', 'MyXGboost'),
    'neural_prophet': ('neural_prophet', 'Neural_Prophet'),
})
