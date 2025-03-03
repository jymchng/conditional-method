import os
import pytest
from conditional_method import conditional_method


@pytest.fixture(autouse=True)
def setup_environment():
    """Set up environment variables for testing"""
    old_debug = os.environ.get("DEBUG", None)
    os.environ["DEBUG"] = "True"
    yield
    if old_debug is None:
        del os.environ["DEBUG"]
    else:
        os.environ["DEBUG"] = old_debug


class TestConditionalMethods:
    def test_class_a_monday_should_use_classmethod(self):
        """Test that A.monday is correctly resolved to the classmethod implementation"""

        # Define test class
        class A:
            """The correct `.monday(..)` is a `classmethod`"""

            __slots__ = ()

            @conditional_method(condition=True)
            def monday(self):
                return "Instance of A " + "A::Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "False"
            )
            def monday(self):
                return "Instance of A " + "A::Another Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "True"
            )
            @classmethod
            def monday(cls):
                return "Class of A " + "A::Yet Another Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "True"
            )  # this is ignored
            @staticmethod
            def monday():
                return "Staticmethod of A" + "A::Yet Another Good Monday"

            def tuesday(self):
                return "Instance of A " + "A::Tuesday"

        # Test class method implementation
        result = A.monday()
        assert result == "Staticmethod of AA::Yet Another Good Monday"

        # Verify it's the same when called on an instance
        instance_result = A().monday()
        assert instance_result == "Staticmethod of AA::Yet Another Good Monday"

        # Test the undecorated method
        assert A().tuesday() == "Instance of A " + "A::Tuesday"
        assert A.tuesday(A()) == "Instance of A " + "A::Tuesday"

    def test_class_b_monday_should_use_instance_method(self):
        """Test that B.monday is correctly resolved to the instance method implementation"""

        class B:
            """The correct `.monday(..)` is a regular instance method"""

            __slots__ = ()

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "False"
            )
            def monday(self):
                return "Instance of B" + "B::Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "True"
            )
            def monday(self):
                return "Instance of B" + "B::Another Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "False"
            )
            def monday(self):
                return "Instance of B" + "B::Yet Another Monday"

            def tuesday(self):
                return "Instance of B" + "B::Tuesday"

        # Test instance method implementation
        result = B().monday()
        assert result == "Instance of B" + "B::Another Monday"

        # Test when called via class
        class_result = B.monday(B())
        assert class_result == "Instance of B" + "B::Another Monday"

        # Test the undecorated method
        assert B().tuesday() == "Instance of B" + "B::Tuesday"
        assert B.tuesday(B()) == "Instance of B" + "B::Tuesday"

    def test_class_c_monday_should_use_staticmethod(self):
        """Test that C.monday is correctly resolved to the staticmethod implementation"""

        class C:
            """The correct `.monday(..)` is a `staticmethod`"""

            __slots__ = ()

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "False"
            )
            def monday(self):
                return "Instance of C" + "C::Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "True"
            )
            @staticmethod
            def monday():
                return "Staticmethod of C" + "C::Another Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "False"
            )
            def monday(self):
                return "Instance of C" + "C:: Yet Monday"

            def tuesday(self):
                return "Instance of C" + "C::Tuesday"

        # Test staticmethod implementation
        result = C.monday()
        assert result == "Staticmethod of C" + "C::Another Monday"

        # Test when called via instance
        instance_result = C().monday()
        assert instance_result == "Staticmethod of C" + "C::Another Monday"

        # Test the undecorated method
        assert C().tuesday() == "Instance of C" + "C::Tuesday"
        assert C.tuesday(C()) == "Instance of C" + "C::Tuesday"

    def test_class_d_monday_should_use_instance_method(self):
        """Test that D.monday is correctly resolved to the instance method implementation"""

        class D:
            """The correct `.monday(..)` is a regular instance method but it is the last `.monday(..)` method defined"""

            __slots__ = ()

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "False"
            )
            def monday(self):
                return "Instance of D" + "D::Monday"

            @conditional_method(
                condition=lambda f: os.environ.get("DEBUG", "False") == "True"
            )
            def monday(self):
                return "Instance of D" + "D::Another Monday"

            def tuesday(self):
                return "Instance of D" + "D::Tuesday"

        # Test instance method implementation
        result = D().monday()
        assert result == "Instance of D" + "D::Another Monday"

        # Test when called via class
        class_result = D.monday(D())
        assert class_result == "Instance of D" + "D::Another Monday"

        # Test the undecorated method
        assert D().tuesday() == "Instance of D" + "D::Tuesday"
        assert D.tuesday(D()) == "Instance of D" + "D::Tuesday"

    def test_normal_staticmethod_behavior(self):
        """Test that a normal staticmethod behaves as expected"""

        class G:
            @staticmethod
            def monday():
                return "Staticmethod of G" + "G::Monday"

        # Test staticmethod
        result = G.monday()
        assert result == "Staticmethod of G" + "G::Monday"

        # Test when called via instance
        instance_result = G().monday()
        assert instance_result == "Staticmethod of G" + "G::Monday"

    def test_all_methods_with_false_condition(self):
        """Test a class where all methods are decorated with False condition"""

        # This should raise a RuntimeError because no condition is True
        with pytest.raises(RuntimeError) as excinfo:

            class AllFalseMethods:
                @conditional_method(condition=False)
                def method1(self):
                    return "This should not be used"

                @conditional_method(condition=False)
                def method2(self):
                    return "This should not be used either"

                @conditional_method(condition=False)
                def method3(self):
                    return "This should not be used as well"

        # Check that the error message mentions the condition issue
        assert (
            "Error calling __set_name__ on 'conditional_method._TypeErrorRaiser' instance 'method1' in 'AllFalseMethods'"
            in str(excinfo.value)
        )
