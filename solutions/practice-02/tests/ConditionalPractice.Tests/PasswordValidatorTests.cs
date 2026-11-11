using ConditionalPractice;
using Xunit;

namespace ConditionalPractice.Tests;

public class PasswordValidatorTests
{
    [Theory]
    [InlineData("12345678", true)]
    [InlineData("1234567", false)]
    [InlineData("", false)]
    public void HasMinLength_checks_eight_characters(string? password, bool expected)
    {
        Assert.Equal(expected, PasswordValidator.HasMinLength(password));
    }

    [Fact]
    public void HasMinLength_rejects_null()
    {
        Assert.False(PasswordValidator.HasMinLength(null));
    }

    [Theory]
    [InlineData("abc1", true)]
    [InlineData("abc", false)]
    [InlineData("", false)]
    public void HasDigit_detects_digit(string password, bool expected)
    {
        Assert.Equal(expected, PasswordValidator.HasDigit(password));
    }

    [Theory]
    [InlineData("aBc", true)]
    [InlineData("abc", false)]
    [InlineData("Пароль", true)]
    public void HasUpper_detects_uppercase(string password, bool expected)
    {
        Assert.Equal(expected, PasswordValidator.HasUpper(password));
    }

    [Theory]
    [InlineData("!", true)]
    [InlineData("@", true)]
    [InlineData("#", true)]
    [InlineData("$", true)]
    [InlineData("%", true)]
    [InlineData("^", true)]
    [InlineData("&", true)]
    [InlineData("*", true)]
    [InlineData("abc", false)]
    public void HasSpecial_accepts_listed_characters(string password, bool expected)
    {
        Assert.Equal(expected, PasswordValidator.HasSpecial(password));
    }

    [Theory]
    [InlineData("Qwerty12!", true)]
    [InlineData("qwerty12!", false)]
    [InlineData("QWERTY12!", true)]
    [InlineData("Qwerty!!", false)]
    [InlineData("Qwerty12", false)]
    [InlineData("Qwert1!", false)]
    [InlineData("", false)]
    public void IsStrong_requires_all_four_rules(string password, bool expected)
    {
        Assert.Equal(expected, PasswordValidator.IsStrong(password));
    }

    [Fact]
    public void IsStrong_rejects_null()
    {
        Assert.False(PasswordValidator.IsStrong(null));
    }
}
