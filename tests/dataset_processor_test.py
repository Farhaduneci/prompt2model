"""Testing TextualizeProcessor."""

import gc
import logging
from copy import deepcopy
from unittest.mock import patch

import datasets
import pytest
from transformers import AutoTokenizer

from prompt2model.dataset_processor.textualize import TextualizeProcessor
from test_helpers import are_dataset_dicts_identical, create_gpt2_model_and_tokenizer

logger = logging.getLogger("DatasetProcessor")

DATASET_DICTS = [
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {
                    "input_col": ["foo", "bar"],
                    "output_col": ["baz", "qux"],
                }
            ),
            "test": datasets.Dataset.from_dict(
                {
                    "input_col": ["foo", "bar"],
                    "output_col": ["baz", "qux"],
                }
            ),
        }
    ),
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {
                    "input_col": ["spam", "eggs"],
                    "output_col": ["ham", "sau"],
                }
            ),
            "val": datasets.Dataset.from_dict(
                {
                    "input_col": ["spam", "eggs"],
                    "output_col": ["ham", "sau"],
                }
            ),
        }
    ),
]


INSTRUCTION = "convert to text2text"

# Our support spilts are `train, val, test`.
UNEXPECTED_DATASET_DICTS_WITH_WRONG_SPLIT = [
    datasets.DatasetDict(
        {
            "full": datasets.Dataset.from_dict(
                {"input_col": ["foo", "bar"], "output_col": ["baz", "qux"]}
            )
        }
    ),
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {"input_col": ["spam", "eggs"], "output_col": ["ham", "sau"]}
            )
        }
    ),
]

# Our support columns are `input_col, output_col`.
UNEXPECTED_DATASET_DICTS_WITH_WRONG_COLUMNS = [
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {"input_col": ["foo", "bar"], "output_col": ["baz", "qux"]}
            )
        }
    ),
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {"input_col": ["spam", "eggs"], "output": ["ham", "sau"]}
            )
        }
    ),
]


def test_the_logging_for_provide_unnecessary_eos_token_for_t5():
    """Test the logger.info for unnecessary eos token for T5 model is logged."""
    t5_tokenizer = AutoTokenizer.from_pretrained("t5-small")

    with patch.object(logger, "info") as mock_info, patch.object(
        logger, "warning"
    ) as mock_warning:
        _ = TextualizeProcessor(has_encoder=True, eos_token=t5_tokenizer.eos_token)
        mock_info.assert_called_once_with(
            "The T5 tokenizer automatically adds eos token in the end of sequence when tokenizing. So the eos_token of encoder-decoder model tokenizer is unnecessary."  # noqa E501
        )
        mock_warning.assert_not_called()
    gc.collect()


def test_the_logging_for_eos_token_required_for_gpt():
    """Test the logger.warning for requiring eos token for GPT model is logged."""
    with patch.object(logger, "info") as mock_info, patch.object(
        logger, "warning"
    ) as mock_warning:
        _ = TextualizeProcessor(has_encoder=False)
        mock_info.assert_not_called()
        mock_warning.assert_called_once_with(
            "The autoregressive model tokenizer does not automatically add eos token in the end of the sequence. So the `eos_token` of the autoregressive model is required."  # noqa E501
        )
    gc.collect()


def test_dataset_processor_t5_style():
    """Test the `process_dataset_dict` function of T5-type `TextualizeProcessor`."""
    t5_processor = TextualizeProcessor(has_encoder=True)
    raw_dataset_dicts = deepcopy(DATASET_DICTS)
    t5_modified_dataset_dicts = t5_processor.process_dataset_dict(
        INSTRUCTION, DATASET_DICTS
    )
    # Ensure the dataset_dicts themselves are the same after processing.
    assert all(
        are_dataset_dicts_identical(raw, origin)
        for (raw, origin) in zip(raw_dataset_dicts, DATASET_DICTS)
    )
    t5_expected_dataset_dicts = [
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\nfoo\nLabel:\n",
                            "<task 0>convert to text2text\nExample:\nbar\nLabel:\n",
                        ],
                        "model_output": ["baz", "qux"],
                    }
                ),
                "test": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\nfoo\nLabel:\n",
                            "<task 0>convert to text2text\nExample:\nbar\nLabel:\n",
                        ],
                        "model_output": ["baz", "qux"],
                    }
                ),
            }
        ),
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 1>convert to text2text\nExample:\nspam\nLabel:\n",
                            "<task 1>convert to text2text\nExample:\neggs\nLabel:\n",
                        ],
                        "model_output": ["ham", "sau"],
                    }
                ),
                "val": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 1>convert to text2text\nExample:\nspam\nLabel:\n",
                            "<task 1>convert to text2text\nExample:\neggs\nLabel:\n",
                        ],
                        "model_output": ["ham", "sau"],
                    }
                ),
            }
        ),
    ]
    for exp, act in zip(t5_expected_dataset_dicts, t5_modified_dataset_dicts):
        assert are_dataset_dicts_identical(exp, act)
    gc.collect()


def test_dataset_processor_with_numerical_column():
    """Test process_dataset_dict with numerical column values."""
    t5_processor = TextualizeProcessor(has_encoder=True)
    raw_dataset_dicts = [
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "input_col": ["foo", "bar"],
                        "output_col": ["baz", "qux"],
                    }
                ),
                "test": datasets.Dataset.from_dict(
                    {
                        "input_col": ["spam", "eggs"],
                        "output_col": ["ham", "sau"],
                    }
                ),
            }
        ),
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "input_col": ["foo", "bar"],
                        "output_col": [0, 1],
                    }
                ),
                "test": datasets.Dataset.from_dict(
                    {
                        "input_col": ["spam", "eggs"],
                        "output_col": [1, 2],
                    }
                ),
            }
        ),
    ]
    t5_modified_dataset_dicts = t5_processor.process_dataset_dict(
        INSTRUCTION, raw_dataset_dicts
    )
    expected_dataset_dict = datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {
                    "model_input": [
                        "<task 0>convert to text2text\nExample:\nfoo\nLabel:\n",
                        "<task 0>convert to text2text\nExample:\nbar\nLabel:\n",
                        "<task 1>convert to text2text\nExample:\nfoo\nLabel:\n",
                        "<task 1>convert to text2text\nExample:\nbar\nLabel:\n",
                    ],
                    "model_output": ["foo", "bar", "0", "1"],
                }
            ),
            "test": datasets.Dataset.from_dict(
                {
                    "model_input": [
                        "<task 0>convert to text2text\nExample:\nspam\nLabel:\n",
                        "<task 0>convert to text2text\nExample:\neggs\nLabel:\n",
                        "<task 1>convert to text2text\nExample:\nspam\nLabel:\n",
                        "<task 1>convert to text2text\nExample:\neggs\nLabel:\n",
                    ],
                    "model_output": ["ham", "sau", "1", "2"],
                }
            ),
        }
    )
    training_datasets = []
    test_datasets = []
    for modified_dataset_dict in t5_modified_dataset_dicts:
        training_datasets.append(modified_dataset_dict["train"])
        test_datasets.append(modified_dataset_dict["test"])

    concatenated_training_dataset = datasets.concatenate_datasets(training_datasets)
    concatenated_test_dataset = datasets.concatenate_datasets(test_datasets)
    actual_dataset_dict = datasets.DatasetDict(
        {"train": concatenated_training_dataset, "test": concatenated_test_dataset}
    )
    are_dataset_dicts_identical(expected_dataset_dict, actual_dataset_dict)

    gc.collect()


def test_dataset_processor_decoder_only_style():
    """Test the `process_dataset_dict` function of a GPT-type `TextualizeProcessor`."""
    _, gpt2_tokenizer = create_gpt2_model_and_tokenizer()
    gpt_processor = TextualizeProcessor(
        has_encoder=False, eos_token=gpt2_tokenizer.eos_token
    )
    raw_dataset_dicts = deepcopy(DATASET_DICTS)
    gpt_modified_dataset_dicts = gpt_processor.process_dataset_dict(
        INSTRUCTION, DATASET_DICTS
    )
    # Ensure the dataset_dicts themselves are the same after processing.
    assert all(
        are_dataset_dicts_identical(raw, origin)
        for raw, origin in zip(raw_dataset_dicts, DATASET_DICTS)
    )
    # Check that the modified dataset dicts have the expected content
    gpt_expected_dataset_dicts = [
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\nfoo\nLabel:\nbaz<|endoftext|>",  # noqa: E501
                            "<task 0>convert to text2text\nExample:\nbar\nLabel:\nqux<|endoftext|>",  # noqa: E501
                        ],
                        "model_output": ["baz<|endoftext|>", "qux<|endoftext|>"],
                    }
                ),
                "test": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\nfoo\nLabel:\n",
                            "<task 0>convert to text2text\nExample:\nbar\nLabel:\n",
                        ],
                        "model_output": ["baz", "qux"],
                    }
                ),
            }
        ),
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 1>convert to text2text\nExample:\nspam\nLabel:\nham<|endoftext|>",  # noqa: E501
                            "<task 1>convert to text2text\nExample:\neggs\nLabel:\nsau<|endoftext|>",  # noqa: E501
                        ],
                        "model_output": ["ham<|endoftext|>", "sau<|endoftext|>"],
                    }
                ),
                "val": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 1>convert to text2text\nExample:\nspam\nLabel:\n",
                            "<task 1>convert to text2text\nExample:\neggs\nLabel:\n",
                        ],
                        "model_output": ["ham", "sau"],
                    }
                ),
            }
        ),
    ]
    assert all(
        are_dataset_dicts_identical(exp, modified)
        for (exp, modified) in zip(
            gpt_expected_dataset_dicts, gpt_modified_dataset_dicts
        )
    )
    gc.collect()


def test_unexpected_dataset_split():
    """Test the error handler for unexpercted dataset split."""
    with pytest.raises(AssertionError) as exc_info:
        _, gpt2_tokenizer = create_gpt2_model_and_tokenizer()
        gpt_processor = TextualizeProcessor(
            has_encoder=False, eos_token=gpt2_tokenizer.eos_token
        )
        _ = gpt_processor.process_dataset_dict(
            INSTRUCTION, UNEXPECTED_DATASET_DICTS_WITH_WRONG_SPLIT
        )
        assert str(exc_info.value) == ("Datset split must be in train/val/test.")
    gc.collect()


def test_unexpected_columns():
    """Test the error handler for unexpercted dataset columns."""
    with pytest.raises(AssertionError) as exc_info:
        _, gpt2_tokenizer = create_gpt2_model_and_tokenizer()
        gpt_processor = TextualizeProcessor(
            has_encoder=False, eos_token=gpt2_tokenizer.eos_token
        )
        _ = gpt_processor.process_dataset_dict(
            INSTRUCTION, UNEXPECTED_DATASET_DICTS_WITH_WRONG_COLUMNS
        )
        assert str(exc_info.value) == (
            "Example dictionary must have 'input_col' and 'output_col' keys."
        )
    gc.collect()


DATASET_DICTS_WITH_EMPTY_COLUMNS = [
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {
                    "input_col": ["foo", "", "test"],
                    "output_col": ["", "qux", "key"],
                }
            ),
            "test": datasets.Dataset.from_dict(
                {
                    "input_col": ["foo", ""],
                    "output_col": ["baz", "qux"],
                }
            ),
        }
    ),
    datasets.DatasetDict(
        {
            "train": datasets.Dataset.from_dict(
                {
                    "input_col": ["", ""],
                    "output_col": ["ham", "sau"],
                }
            ),
        }
    ),
]


def test_empty_filter_t5_type():
    """Test that examples with empty input_col or output_col are discarded."""
    t5_processor = TextualizeProcessor(has_encoder=True)
    t5_modified_dataset_dicts = t5_processor.process_dataset_dict(
        INSTRUCTION, DATASET_DICTS_WITH_EMPTY_COLUMNS
    )
    t5_expected_dataset_dicts = [
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\ntest\nLabel:\n",
                        ],
                        "model_output": ["key"],
                    }
                ),
                "test": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\nfoo\nLabel:\n",
                        ],
                        "model_output": [
                            "baz",
                        ],
                    }
                ),
            }
        ),
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [],
                        "model_output": [],
                    }
                ),
            }
        ),
    ]
    assert all(
        are_dataset_dicts_identical(exp, act)
        for exp, act in zip(t5_expected_dataset_dicts, t5_modified_dataset_dicts)
    )
    gc.collect()


def test_empty_filter_decoder_only_style():
    """Test the `process_dataset_dict` function of a GPT-type `TextualizeProcessor`."""
    _, gpt2_tokenizer = create_gpt2_model_and_tokenizer()
    gpt_processor = TextualizeProcessor(
        has_encoder=False, eos_token=gpt2_tokenizer.eos_token
    )
    gpt_modified_dataset_dicts = gpt_processor.process_dataset_dict(
        INSTRUCTION, DATASET_DICTS_WITH_EMPTY_COLUMNS
    )

    # Check that the modified dataset dicts have the expected content
    gpt_expected_dataset_dicts = [
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\ntest\nLabel:\nkey<|endoftext|>",  # noqa: E501
                        ],
                        "model_output": ["key<|endoftext|>"],
                    }
                ),
                "test": datasets.Dataset.from_dict(
                    {
                        "model_input": [
                            "<task 0>convert to text2text\nExample:\nfoo\nLabel:\n",
                        ],
                        "model_output": ["baz"],
                    }
                ),
            }
        ),
        datasets.DatasetDict(
            {
                "train": datasets.Dataset.from_dict(
                    {
                        "model_input": [],
                        "model_output": [],
                    }
                ),
            }
        ),
    ]
    assert all(
        are_dataset_dicts_identical(expected, modified)
        for expected, modified in zip(
            gpt_expected_dataset_dicts, gpt_modified_dataset_dicts
        )
    )
    gc.collect()
