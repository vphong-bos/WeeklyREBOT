from app.utils.adf import adf_to_text


def test_adf_to_text_paragraph():
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Hello Jira"},
                ],
            }
        ],
    }

    assert adf_to_text(adf).strip() == "Hello Jira"


def test_adf_to_text_bullet_list():
    adf = {
        "type": "doc",
        "content": [
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Done task A"}],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    assert "Done task A" in adf_to_text(adf)