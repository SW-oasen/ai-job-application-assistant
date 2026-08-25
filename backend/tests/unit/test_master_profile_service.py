from app.services.master_profile_service import normalized_master_profile_content


def test_master_profile_comparison_ignores_whitespace_and_line_breaks() -> None:
    assert normalized_master_profile_content("# profile_name\nYuchuan Liu\n") == (
        normalized_master_profile_content(" # profile_name  Yuchuan\tLiu ")
    )


def test_master_profile_comparison_detects_content_changes() -> None:
    assert normalized_master_profile_content("# profile_name\nYuchuan Liu") != (
        normalized_master_profile_content("# profile_name\nAnother Person")
    )
